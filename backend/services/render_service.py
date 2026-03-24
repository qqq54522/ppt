import os
import re
import base64
import logging
from pathlib import Path

from playwright.sync_api import sync_playwright

from utils.path_utils import UPLOAD_FOLDER

logger = logging.getLogger(__name__)


def _strip_body_wrapper(html: str) -> str:
    """Strip outer <body ...> and </body> tags from AI-generated HTML content.

    AI often returns HTML wrapped in <body style="...">...</body>.
    When we embed this inside our own <body> (which carries the background image),
    the nested body's inline styles override the outer body's background.
    """
    stripped = html.strip()
    stripped = re.sub(
        r"^<body\b[^>]*>", "", stripped, count=1, flags=re.IGNORECASE | re.DOTALL
    )
    stripped = re.sub(
        r"</body\s*>\s*$", "", stripped, count=1, flags=re.IGNORECASE
    )
    return stripped.strip()

SLIDE_WIDTH = 1920
SLIDE_HEIGHT = 1080


def _bg_image_data_uri(bg_path: str | None) -> str:
    """将相对路径的背景图片转为 base64 data URI，嵌入 HTML 中。

    使用 data URI 而非 file:/// 协议，因为 Playwright 的 set_content
    将 HTML 注入 about:blank，Chromium 会阻止跨域加载 file:/// 资源。
    """
    if not bg_path:
        return ""
    abs_path = os.path.join(UPLOAD_FOLDER, bg_path)
    if not os.path.isfile(abs_path):
        logger.warning("Background image not found: %s", abs_path)
        return ""
    try:
        with open(abs_path, "rb") as f:
            raw = f.read()
        ext = os.path.splitext(abs_path)[1].lower()
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "webp": "image/webp", "gif": "image/gif"}.get(ext.lstrip("."), "image/png")
        b64 = base64.b64encode(raw).decode()
        return f"data:{mime};base64,{b64}"
    except Exception as e:
        logger.warning("Failed to read background image %s: %s", abs_path, e)
        return ""


def build_full_html(html_content: str, bg_path: str | None = None) -> str:
    """构建完整 HTML：视觉层图片作为 body 背景 + 文字层 HTML 叠加。

    方案C混合架构：
    - bg_path 可以是每页独立的视觉层图片，也可以是全局底图模板
    - html_content 是透明背景的文字层 HTML
    - 两者合成 = 视觉丰富 + 文字清晰

    AI 生成的 html_content 通常包含 <body style="..."> 标签，
    必须剥离以避免嵌套 body 覆盖外层背景图。
    """
    bg_uri = _bg_image_data_uri(bg_path)
    bg_css = (
        f"background-image:url('{bg_uri}');background-size:cover;background-position:center;"
        if bg_uri
        else "background:#1e293b;"
    )

    inner_html = _strip_body_wrapper(html_content)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700;900&display=swap');
  body {{
    width:{SLIDE_WIDTH}px;
    height:{SLIDE_HEIGHT}px;
    overflow:hidden;
    position:relative;
    font-family:'Noto Sans SC','Microsoft YaHei','PingFang SC',sans-serif;
    -webkit-font-smoothing:antialiased;
    color:#FFFFFF;
    {bg_css}
  }}
</style>
</head>
<body>
{inner_html}
</body>
</html>"""


def render_html_to_image(
    html_content: str,
    output_path: str,
    bg_path: str | None = None,
) -> str:
    """Render HTML content to a PNG image using Playwright + system Chrome."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    full_html = build_full_html(html_content, bg_path)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            headless=True,
        )
        page = browser.new_page(
            viewport={"width": SLIDE_WIDTH, "height": SLIDE_HEIGHT},
            device_scale_factor=2,
        )
        page.set_content(full_html, wait_until="networkidle")
        page.wait_for_timeout(500)
        page.screenshot(path=output_path, type="png")
        browser.close()

    logger.info("Rendered slide to %s", output_path)
    return output_path


def render_slide_for_project(
    html_content: str,
    project_id: str,
    filename: str,
    bg_path: str | None = None,
) -> str:
    """Render and save, returning the relative path under uploads/."""
    from utils.path_utils import get_project_images_folder

    folder = get_project_images_folder(project_id)
    output_path = os.path.join(folder, filename)
    render_html_to_image(html_content, output_path, bg_path)

    rel = os.path.relpath(output_path, UPLOAD_FOLDER)
    return rel.replace("\\", "/")
