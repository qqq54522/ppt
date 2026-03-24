import os
import json
import base64
import logging
import re
from io import BytesIO
from pathlib import Path

import httpx
from openai import APIStatusError, APITimeoutError, APIConnectionError, OpenAI
from PIL import Image
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from config import Config
from services.prompts import (
    get_outline_prompt, get_image_prompt,
    get_replace_text_prompt, get_mask_edit_prompt,
    get_global_style_gen_messages,
    get_background_template_prompt, get_content_layer_prompt,
    DOCUMENT_ANALYSIS_PROMPT, IMAGE_GEN_SYSTEM_PROMPT,
)
from utils.path_utils import get_project_images_folder

logger = logging.getLogger(__name__)

_ai_service = None


def get_ai_service():
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service


class AIService:
    def __init__(self):
        self.client = OpenAI(
            api_key=Config.OPENAI_API_KEY,
            base_url=Config.OPENAI_API_BASE,
            timeout=httpx.Timeout(120, connect=30),
        )
        self.text_model = Config.TEXT_MODEL
        self.image_model = Config.IMAGE_MODEL
        self._images_endpoint_supported: bool | None = None

        self.ark_client = None
        if Config.ARK_API_KEY and Config.ARK_API_KEY != "你的火山引擎API Key":
            self.ark_client = OpenAI(
                api_key=Config.ARK_API_KEY,
                base_url=Config.ARK_API_BASE,
            )
            self.ark_image_model = Config.ARK_IMAGE_MODEL
            logger.info(
                "火山 Ark（豆包）已启用：endpoint=%s model=%s；"
                "遮罩重绘会调用图生图。USE_ARK_FOR_SLIDE_IMAGES=%s 时整页生成也走 Ark。",
                Config.ARK_API_BASE,
                self.ark_image_model,
                Config.USE_ARK_FOR_SLIDE_IMAGES,
            )
        else:
            logger.warning(
                "未配置有效 ARK_API_KEY：遮罩重绘将跳过豆包图生图，并回退到 OPENAI 通道整页重绘。"
                "请在 backend/.env 中设置 ARK_API_KEY（火山引擎 API Key）。"
            )

    # ── Text generation (analysis model) ──

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=4, max=30),
        retry=retry_if_exception_type((APITimeoutError, APIConnectionError)),
    )
    def _chat(self, messages: list[dict], model: str | None = None) -> str:
        resp = self.client.chat.completions.create(
            model=model or self.text_model,
            messages=messages,
            temperature=0.7,
            max_tokens=8192,
        )
        return resp.choices[0].message.content or ""

    def _chat_json(self, messages: list[dict]) -> dict:
        raw = self._chat(messages)
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        text = match.group(1).strip() if match else raw.strip()
        if text.startswith("{"):
            return json.loads(text)
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
        raise ValueError(f"Cannot parse JSON from response: {raw[:200]}")

    def _chat_with_images(self, prompt: str, image_paths: list[str]) -> str:
        content: list[dict] = [{"type": "text", "text": prompt}]
        for img_path in image_paths:
            b64 = self._encode_image(img_path)
            if b64:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"},
                })
        messages = [{"role": "user", "content": content}]
        return self._chat(messages)

    def _chat_json_with_images(self, prompt: str, image_paths: list[str]) -> dict:
        raw = self._chat_with_images(prompt, image_paths)
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        text = match.group(1).strip() if match else raw.strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
        raise ValueError(f"Cannot parse JSON from image response: {raw[:200]}")

    @staticmethod
    def _encode_image(path: str) -> str | None:
        try:
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode()
        except Exception:
            return None

    # ── Image generation ──

    def _try_ark_text_to_image(self, prompt: str, aspect_ratio: str) -> bytes | None:
        """火山 Ark 文生图（与遮罩图生图共用 Ark 凭证）。"""
        if not self.ark_client or not Config.USE_ARK_FOR_SLIDE_IMAGES:
            return None
        size = "1792x1024" if aspect_ratio == "16:9" else "1024x1024"
        logger.info(
            "正在调用火山 Ark 豆包文生图: model=%s size=%s",
            self.ark_image_model,
            size,
        )
        try:
            resp = self.ark_client.images.generate(
                model=self.ark_image_model,
                prompt=prompt,
                n=1,
                size=size,
                response_format="b64_json",
            )
            if resp.data and resp.data[0].b64_json:
                logger.info("火山 Ark 豆包文生图成功（b64）")
                return base64.b64decode(resp.data[0].b64_json)
            if resp.data and resp.data[0].url:
                import urllib.request

                logger.info("火山 Ark 豆包文生图成功（url）")
                with urllib.request.urlopen(resp.data[0].url) as r:
                    return r.read()
        except Exception as e:
            logger.warning("火山 Ark 文生图失败，将尝试其它通道: %s", e)
        return None

    def _generate_image_api(self, prompt: str, aspect_ratio: str = "16:9",
                             input_images: list[str] | None = None,
                             input_image_bytes: list[bytes] | None = None) -> bytes | None:
        if (
            not input_images
            and not input_image_bytes
            and Config.USE_ARK_FOR_SLIDE_IMAGES
        ):
            img = self._try_ark_text_to_image(prompt, aspect_ratio)
            if img:
                return img
        if not input_images and not input_image_bytes and self._images_endpoint_supported is not False:
            img = self._try_images_endpoint(prompt, aspect_ratio)
            if img:
                self._images_endpoint_supported = True
                return img
            self._images_endpoint_supported = False
        return self._try_chat_image(prompt, aspect_ratio, input_images, input_image_bytes)

    def _try_images_endpoint(self, prompt: str, aspect_ratio: str) -> bytes | None:
        try:
            size = "1792x1024" if aspect_ratio == "16:9" else "1024x1024"
            resp = self.client.images.generate(
                model=self.image_model,
                prompt=prompt,
                n=1,
                size=size,
            )
            if resp.data and resp.data[0].b64_json:
                return base64.b64decode(resp.data[0].b64_json)
            if resp.data and resp.data[0].url:
                import urllib.request
                with urllib.request.urlopen(resp.data[0].url) as r:
                    return r.read()
        except Exception as e:
            logger.warning("images.generate failed, falling back to chat: %s", e)
        return None

    def _try_chat_image(self, prompt: str, aspect_ratio: str,
                         input_images: list[str] | None = None,
                         input_image_bytes: list[bytes] | None = None) -> bytes | None:
        content: list[dict] = []
        for img_path in (input_images or []):
            b64 = self._encode_image(img_path)
            if b64:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"},
                })
        for raw_bytes in (input_image_bytes or []):
            b64 = base64.b64encode(raw_bytes).decode()
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}"},
            })
        content.append({"type": "text", "text": prompt})
        try:
            resp = self.client.chat.completions.create(
                model=self.image_model,
                messages=[{"role": "user", "content": content}],
                max_tokens=8192,
            )
            raw = resp.choices[0].message.content or ""
            match = re.search(r"data:image/[^;]+;base64,([A-Za-z0-9+/=]+)", raw)
            if match:
                return base64.b64decode(match.group(1))
            logger.error("Chat image response contained no image data")
        except Exception as e:
            logger.error("Chat-based image generation failed: %s", e)
        return None

    def _save_image(self, image_bytes: bytes, project_id: str, filename: str) -> str:
        folder = get_project_images_folder(project_id)
        filepath = os.path.join(folder, filename)
        with open(filepath, "wb") as f:
            f.write(image_bytes)
        rel = os.path.relpath(filepath, Path(__file__).resolve().parent.parent.parent / "uploads")
        return rel.replace("\\", "/")

    # ── Public methods ──

    def analyze_document(self, file_path: str, file_type: str) -> dict:
        if file_type == "pdf":
            return self._analyze_pdf(file_path)
        else:
            return self._analyze_text_file(file_path)

    def _analyze_pdf(self, file_path: str) -> dict:
        import fitz
        doc = fitz.open(file_path)
        image_paths = []
        temp_dir = os.path.join(os.path.dirname(file_path), "_pdf_pages")
        os.makedirs(temp_dir, exist_ok=True)

        page_count = min(doc.page_count, 20)
        for i in range(page_count):
            page = doc[i]
            pix = page.get_pixmap(dpi=150)
            img_path = os.path.join(temp_dir, f"page_{i+1}.png")
            pix.save(img_path)
            image_paths.append(img_path)

        doc.close()

        if len(image_paths) <= 10:
            result = self._chat_json_with_images(DOCUMENT_ANALYSIS_PROMPT, image_paths)
        else:
            batch1 = self._chat_with_images(
                "请分析这些页面内容，提取所有关键信息、要点和数据。输出详细摘要。",
                image_paths[:10],
            )
            batch2 = self._chat_with_images(
                "请分析这些页面内容，提取所有关键信息、要点和数据。输出详细摘要。",
                image_paths[10:],
            )
            merge_prompt = (
                f"{DOCUMENT_ANALYSIS_PROMPT}\n\n"
                f"第一部分摘要：\n{batch1}\n\n第二部分摘要：\n{batch2}"
            )
            result = self._chat_json([{"role": "user", "content": merge_prompt}])

        return result

    def _analyze_text_file(self, file_path: str) -> dict:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        except UnicodeDecodeError:
            with open(file_path, "r", encoding="gbk") as f:
                text = f.read()

        if len(text) > 50000:
            chunks = [text[i:i+25000] for i in range(0, len(text), 25000)]
            summaries = []
            for chunk in chunks[:3]:
                s = self._chat([{"role": "user", "content": f"请摘要以下内容：\n\n{chunk}"}])
                summaries.append(s)
            combined = "\n\n".join(summaries)
            prompt = f"{DOCUMENT_ANALYSIS_PROMPT}\n\n文档内容摘要：\n{combined}"
        else:
            prompt = f"{DOCUMENT_ANALYSIS_PROMPT}\n\n文档内容：\n{text}"

        return self._chat_json([{"role": "user", "content": prompt}])

    def generate_outline(self, project) -> dict:
        content = project.idea_prompt or project.outline_text or ""
        analysis = project.document_analysis if project.creation_type == "upload" else None

        if analysis and "ref_file_id" in (analysis or {}):
            from models.reference_file import ReferenceFile
            from models import db
            ref = db.session.get(ReferenceFile, analysis["ref_file_id"])
            if ref and ref.analysis_result:
                analysis = ref.analysis_result

        messages = get_outline_prompt(project.creation_type, content, analysis)
        return self._chat_json(messages)

    def _ensure_global_style_prompt(self, project) -> dict:
        """确保 style_config 中存在 global_style_prompt；若没有则用 AI 生成并持久化。"""
        from models import db

        style_config = project.style_config or {}
        if style_config.get("global_style_prompt"):
            return style_config

        ref_desc = ""
        ref_images = style_config.get("reference_images", [])
        if ref_images:
            ref_desc = self._get_ref_style_description(ref_images) or ""

        messages = get_global_style_gen_messages(style_config, ref_desc)
        try:
            global_prompt = self._chat(messages)
            logger.info("已生成全局风格锚定提示词（%d 字）", len(global_prompt))
        except Exception as e:
            logger.warning("生成全局风格锚定失败，将使用空值: %s", e)
            global_prompt = ""

        if global_prompt:
            style_config["global_style_prompt"] = global_prompt
            project.style_config = style_config
            db.session.commit()

        return style_config

    def _get_ref_style_description(self, ref_images: list[str]) -> str | None:
        from utils.path_utils import UPLOAD_FOLDER

        abs_paths = [
            os.path.join(UPLOAD_FOLDER, r)
            for r in ref_images
            if os.path.isfile(os.path.join(UPLOAD_FOLDER, r))
        ]
        if not abs_paths:
            return None
        try:
            return self._chat_with_images(
                "请详细描述这些图片的视觉风格，包括：配色方案、背景风格、排版布局、字体风格、装饰元素。"
                "只输出风格描述，不要分析内容。控制在200字以内。",
                abs_paths,
            )
        except Exception as e:
            logger.warning("Failed to analyze reference images: %s", e)
            return None

    def generate_background_template(self, project) -> str:
        """生成统一底图模板并保存到项目，返回相对路径。"""
        from models import db

        style_config = self._ensure_global_style_prompt(project)
        prompt = get_background_template_prompt(style_config)
        aspect = style_config.get("aspect_ratio", "16:9")

        img_bytes = self._generate_image_api(prompt, aspect)
        if not img_bytes:
            raise RuntimeError("生成底图模板失败")

        filename = f"bg_template_{os.urandom(4).hex()}.png"
        rel_path = self._save_image(img_bytes, project.id, filename)

        style_config["background_template"] = rel_path
        project.style_config = style_config
        db.session.commit()
        logger.info("已生成底图模板: %s", rel_path)
        return rel_path

    def _load_background_template(self, style_config: dict) -> bytes | None:
        """加载底图模板的原始字节。"""
        from utils.path_utils import UPLOAD_FOLDER

        bg_path = style_config.get("background_template")
        if not bg_path:
            return None
        abs_path = os.path.join(UPLOAD_FOLDER, bg_path)
        if not os.path.isfile(abs_path):
            logger.warning("底图模板文件不存在: %s", abs_path)
            return None
        with open(abs_path, "rb") as f:
            return f.read()

    def generate_slide_image(self, project, page) -> str:
        style_config = self._ensure_global_style_prompt(project)
        is_cover = page.page_number == 1
        total = len(project.pages)
        is_ending = page.page_number == total
        aspect = style_config.get("aspect_ratio", "16:9")

        bg_bytes = self._load_background_template(style_config)

        if bg_bytes:
            prompt = get_content_layer_prompt(
                page.title, page.content, page.relationship_type,
                style_config, is_cover=is_cover, is_ending=is_ending,
            )
            img_bytes = self._generate_image_api(
                prompt, aspect, input_image_bytes=[bg_bytes],
            )
        else:
            prompt = get_image_prompt(
                page.title, page.content, page.relationship_type,
                style_config, is_cover=is_cover, is_ending=is_ending,
            )
            ref_images = style_config.get("reference_images", [])
            if ref_images and not style_config.get("global_style_prompt"):
                prompt = self._enrich_prompt_with_ref_description(
                    prompt, ref_images, style_config,
                )
            img_bytes = self._generate_image_api(prompt, aspect)

        if not img_bytes:
            raise RuntimeError(f"Failed to generate image for page {page.page_number}")

        filename = f"page_{page.page_number}_{os.urandom(4).hex()}.png"
        return self._save_image(img_bytes, project.id, filename)

    def _enrich_prompt_with_ref_description(self, prompt: str, ref_images: list[str], style_config: dict) -> str:
        from utils.path_utils import UPLOAD_FOLDER
        abs_paths = [os.path.join(UPLOAD_FOLDER, r) for r in ref_images if os.path.isfile(os.path.join(UPLOAD_FOLDER, r))]
        if not abs_paths:
            return prompt
        try:
            description = self._chat_with_images(
                "请详细描述这些图片的视觉风格，包括：配色方案、背景风格、排版布局、字体风格、装饰元素。"
                "只输出风格描述，不要分析内容。控制在200字以内。",
                abs_paths,
            )
            return prompt + f"\n\n参考风格描述：{description}\n请严格按照上述视觉风格设计。"
        except Exception as e:
            logger.warning("Failed to analyze reference images: %s", e)
            return prompt

    def _build_page_prompt(self, page, style_config: dict, content_override: str | None = None) -> str:
        is_cover = page.page_number == 1
        total = len(page.project.pages)
        is_ending = page.page_number == total
        content = content_override if content_override is not None else page.content
        return get_image_prompt(
            page.title, content, page.relationship_type,
            style_config, is_cover=is_cover, is_ending=is_ending,
        )

    def replace_text_in_slide(self, page, old_text: str, new_text: str, extra_prompt: str = "") -> str:
        style_config = page.project.style_config or {}
        new_content = page.content.replace(old_text, new_text)
        new_title = page.title.replace(old_text, new_text)

        prompt = self._build_page_prompt(page, style_config, content_override=new_content)
        if new_title != page.title:
            prompt = prompt.replace(page.title, new_title)
        if extra_prompt:
            prompt += f"\n\n额外要求：{extra_prompt}"
        prompt += f"\n\n重要：请确保文字「{new_text}」在页面中清晰呈现。"

        aspect = style_config.get("aspect_ratio", "16:9")
        img_bytes = self._generate_image_api(prompt, aspect)
        if not img_bytes:
            raise RuntimeError("Failed to generate replacement image")

        filename = f"page_{page.page_number}_edit_{os.urandom(4).hex()}.png"
        return self._save_image(img_bytes, page.project_id, filename)

    def mask_edit_slide(self, page, region: dict, prompt: str) -> str:
        from utils.path_utils import UPLOAD_FOLDER
        abs_path = os.path.join(UPLOAD_FOLDER, page.image_path)

        x, y = int(region.get("x", 0)), int(region.get("y", 0))
        w, h = int(region.get("width", 0)), int(region.get("height", 0))

        original = Image.open(abs_path)
        x2 = min(x + w, original.width)
        y2 = min(y + h, original.height)
        cropped = original.crop((x, y, x2, y2))

        buf = BytesIO()
        cropped.save(buf, format="PNG")
        crop_bytes = buf.getvalue()
        crop_b64 = base64.b64encode(crop_bytes).decode()
        logger.info("Mask edit: cropped %dx%d, %d bytes", x2 - x, y2 - y, len(crop_bytes))

        gen_prompt = (
            f"基于这张图片进行修改：{prompt}\n"
            f"保持相同的视觉风格、配色和背景，仅做要求的修改。"
        )

        # 豆包返回的是「局部块」，需贴回原图；OPENAI 通道多为「整页新图」，不能再做局部 composite
        use_patch_composite = False
        gen_bytes = self._doubao_image_edit(gen_prompt, crop_b64)
        if gen_bytes:
            use_patch_composite = True
        else:
            logger.warning(
                "豆包图生图未返回结果，将依次回退：带原图的多模态生成 → 纯文生图"
            )
            style_config = page.project.style_config or {}
            aspect = style_config.get("aspect_ratio", "16:9")
            with open(abs_path, "rb") as f:
                full_png = f.read()
            region_hint = (
                f"需要修改的矩形区域（像素，相对整图左上角）：x={x}, y={y}, "
                f"宽={x2 - x}, 高={y2 - y}。"
            )
            mm_prompt = (
                self._build_page_prompt(page, style_config)
                + f"\n\n{region_hint}\n用户修改要求：{prompt}\n"
                "请根据所附的当前幻灯片图片输出一张**完整**的新幻灯片："
                "仅按上述要求改动指定区域，其余版式、文字与风格尽量与原图一致。"
            )
            gen_bytes = self._generate_image_api(
                mm_prompt, aspect, input_image_bytes=[full_png]
            )
            if not gen_bytes:
                fallback_prompt = self._build_page_prompt(page, style_config)
                fallback_prompt += f"\n\n用户要求修改：{prompt}"
                gen_bytes = self._generate_image_api(fallback_prompt, aspect)
        if not gen_bytes:
            raise RuntimeError(
                "遮罩重绘失败：豆包无返回，且 OPENAI 通道（含带图多模态）也未生成图片。"
                "请检查 ARK_API_KEY、OPENAI_API_KEY 与模型是否支持出图，并查看后端日志中的具体报错。"
            )

        if use_patch_composite:
            result_bytes = self._composite_mask_from_bytes(abs_path, gen_bytes, x, y, x2, y2)
        else:
            result_bytes = gen_bytes

        filename = f"page_{page.page_number}_mask_{os.urandom(4).hex()}.png"
        return self._save_image(result_bytes, page.project_id, filename)

    def _doubao_image_edit(self, prompt: str, image_b64: str) -> bytes | None:
        if not self.ark_client:
            logger.warning("未初始化 Ark 客户端，跳过豆包图生图（请检查 backend/.env 中 ARK_API_KEY）")
            return None
        data_uri = f"data:image/png;base64,{image_b64}"
        # 方舟文档中 reference 多为纯 base64 或 URL；多试几种载荷以提高成功率
        extra_variants: list[dict] = [
            {"image": image_b64},
            {"image": data_uri},
        ]
        import urllib.request

        for extra in extra_variants:
            try:
                logger.info(
                    "正在调用火山 Ark 豆包图生图（遮罩编辑）: model=%s crop_b64_len=%d extra_keys=%s",
                    self.ark_image_model,
                    len(image_b64),
                    list(extra.keys()),
                )
                resp = self.ark_client.images.generate(
                    model=self.ark_image_model,
                    prompt=prompt,
                    size="1024x1024",
                    response_format="b64_json",
                    extra_body=extra,
                )
                if not resp.data:
                    logger.warning(
                        "火山 Ark 图生图返回 data 为空（可能被拒或参数不匹配），将尝试下一载荷"
                    )
                    continue
                if resp.data[0].b64_json:
                    logger.info("火山 Ark 豆包图生图成功（b64）")
                    return base64.b64decode(resp.data[0].b64_json)
                if resp.data[0].url:
                    logger.info("火山 Ark 豆包图生图成功（url）")
                    with urllib.request.urlopen(resp.data[0].url) as r:
                        return r.read()
                logger.warning("火山 Ark 返回的条目无 b64_json/url: %s", resp.data[0])
            except APIStatusError as e:
                st = e.response.status_code if e.response is not None else None
                logger.error(
                    "火山 Ark 豆包图生图 HTTP 错误 status=%s body=%s",
                    st,
                    e.body if e.body is not None else str(e),
                )
            except Exception as e:
                logger.error("火山 Ark 豆包图生图失败: %s", e)
        return None

    @staticmethod
    def _composite_mask_from_bytes(original_path: str, gen_bytes: bytes,
                                    x: int, y: int, x2: int, y2: int) -> bytes:
        original = Image.open(original_path).convert("RGBA")
        generated = Image.open(BytesIO(gen_bytes)).convert("RGBA")

        target_w, target_h = x2 - x, y2 - y
        patch = generated.resize((target_w, target_h), Image.LANCZOS)

        feather = min(8, target_w // 4, target_h // 4)
        mask = Image.new("L", (target_w, target_h), 255)
        for i in range(feather):
            alpha = int(255 * (i + 1) / (feather + 1))
            for px in range(target_w):
                mask.putpixel((px, i), min(mask.getpixel((px, i)), alpha))
                mask.putpixel((px, target_h - 1 - i), min(mask.getpixel((px, target_h - 1 - i)), alpha))
            for py in range(target_h):
                mask.putpixel((i, py), min(mask.getpixel((i, py)), alpha))
                mask.putpixel((target_w - 1 - i, py), min(mask.getpixel((target_w - 1 - i, py)), alpha))

        original.paste(patch, (x, y), mask)
        buf = BytesIO()
        original.convert("RGB").save(buf, format="PNG")
        return buf.getvalue()


def generate_images_task(task_id: str, project_id: str, page_ids: list[str] | None = None):
    from models import db
    from models.project import Project
    from models.page import Page
    from services.task_manager import update_task_progress

    project = db.session.get(Project, project_id)
    if not project:
        raise ValueError("Project not found")

    ai = get_ai_service()
    pages = project.pages
    if page_ids:
        pages = [p for p in pages if p.id in page_ids]

    total = len(pages)
    for i, page in enumerate(pages):
        try:
            image_path = ai.generate_slide_image(project, page)
            if page.image_path:
                versions = page.image_versions or []
                versions.append(page.image_path)
                page.image_versions = versions
            page.image_path = image_path
            page.status = "generated"
            db.session.commit()
        except Exception as e:
            logger.error("Failed to generate page %d: %s", page.page_number, e)
            page.status = "failed"
            db.session.commit()

        update_task_progress(task_id, ((i + 1) / total) * 100)
