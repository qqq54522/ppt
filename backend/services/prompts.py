RELATIONSHIP_VISUAL_MAP = {
    "parallel": "使用并排卡片或网格布局展示各要点，平等排列。",
    "progressive": "使用阶梯式递进图、时间线或向右/向下的箭头流程展示层层递进关系。",
    "hierarchical": "使用中心发散的树状图、脑图或总分结构图，突出核心与分支。",
    "causal": "使用因果链流程图，用箭头连接原因与结果。",
    "comparison": "使用左右对比双栏布局或 VS 对比图，清晰展示差异。",
    "data": "使用数据可视化图表（雷达图、饼图、柱状图等），直观展示数据。",
    "process": "使用带编号的流程图或步骤图，用箭头连接各步骤。",
}

OUTLINE_SYSTEM_PROMPT = """你是一名专业的演示文稿大纲规划师。
根据用户提供的内容，生成一份结构清晰的 PPT 大纲。

输出要求（JSON 格式）：
{
  "title": "演示文稿标题",
  "outline_text": "大纲的纯文本 Markdown 版本",
  "pages": [
    {
      "title": "页面标题",
      "content": "该页面详细内容描述，包含所有要展示的文字和要点",
      "relationship": "内容关系类型"
    }
  ]
}

relationship 必须为以下之一：
- none: 无特殊关系
- parallel: 并列关系（多个平等要点）
- progressive: 递进关系（层层深入）
- hierarchical: 总分关系（一个核心，多个分支）
- causal: 因果关系（原因→结果）
- comparison: 对比关系（A vs B）
- data: 数据展示（包含数字/统计）
- process: 流程关系（步骤1→步骤2→...）

规则：
1. 第一页必须是封面页，最后一页是总结/感谢页
2. 总页数 8-15 页，根据内容复杂度调整
3. 每页内容描述要详细，包含所有需要展示的文字
4. 自动识别内容之间的逻辑关系并标注
5. 输出语言与用户输入语言一致
"""

OUTLINE_FROM_ANALYSIS_PROMPT = """你是一名专业的演示文稿大纲规划师。
以下是对一份文档的 AI 分析结果，请据此生成 PPT 大纲。

文档分析结果：
{analysis}

请按照 JSON 格式输出大纲，格式同上。注意提取文档中的核心信息，合理组织页面结构。"""


def get_outline_prompt(creation_type: str, content: str, analysis: dict | None = None) -> list[dict]:
    messages = [{"role": "system", "content": OUTLINE_SYSTEM_PROMPT}]
    if creation_type == "upload" and analysis:
        messages.append({
            "role": "user",
            "content": OUTLINE_FROM_ANALYSIS_PROMPT.format(analysis=str(analysis)),
        })
    elif creation_type == "idea":
        messages.append({
            "role": "user",
            "content": f"请根据以下主题生成 PPT 大纲：\n\n{content}",
        })
    elif creation_type == "outline":
        messages.append({
            "role": "user",
            "content": f"请根据以下大纲内容，补充完善并生成标准格式的 PPT 大纲：\n\n{content}",
        })
    return messages


IMAGE_GEN_SYSTEM_PROMPT = """你是一名专业的 PPT 页面设计师，擅长创建高质量的演示文稿页面图像。
根据描述生成一张精美的 PPT 页面图片。

设计规范：
1. 页面为标准 PPT 页面，{aspect_ratio} 比例
2. 背景干净，排版专业
3. 文字清晰可读，字号适中
4. 使用合适的配色方案
5. 包含必要的图标、插图或图表来增强视觉效果
6. 所有文字内容必须精确渲染，不允许出现乱码或模糊文字"""


GLOBAL_STYLE_GEN_PROMPT = """\
你是一名资深视觉设计总监。请根据以下信息，输出一段 **150-250 字** 的统一视觉风格规范，
后续所有幻灯片页面都将严格遵守这段规范，以确保全套 PPT 风格一致。

规范必须涵盖：
1. 主色 / 辅色 / 强调色的具体色值或色名
2. 背景风格（纯色 / 渐变 / 纹理 / 图片蒙版等）
3. 标题与正文的字体风格、粗细、大小层级
4. 排版基调（对齐方式、留白比例、信息密度）
5. 装饰元素风格（线条、图标、几何图形、插图等）
6. 整体调性关键词（如：专业、简约、科技感、温暖…）

只输出规范文本，不要解释、不要 JSON。
"""


def _build_global_style_gen_input(style_config: dict) -> str:
    """将用户已有的风格配置拼成给 AI 的输入段。"""
    lines: list[str] = []
    preset = style_config.get("preset")
    if preset:
        preset_labels = {
            "business": "商务专业风格，深蓝色系，简洁大方",
            "academic": "学术风格，白底黑字，严谨规范",
            "tech": "科技风格，深色渐变背景，霓虹蓝/紫点缀",
            "minimal": "极简风格，大量留白，少量色彩",
            "creative": "创意风格，色彩丰富，自由排版",
            "education": "教育风格，温暖色调，清晰易读",
        }
        lines.append(f"预设风格：{preset_labels.get(preset, preset)}")
    if style_config.get("style_description"):
        lines.append(f"用户风格描述：{style_config['style_description']}")
    if style_config.get("aspect_ratio"):
        lines.append(f"画面比例：{style_config['aspect_ratio']}")
    return "\n".join(lines) if lines else "用户未指定特定风格，请自行设计一套专业美观的视觉规范。"


def get_global_style_gen_messages(style_config: dict,
                                  ref_style_description: str = "") -> list[dict]:
    """构造用于生成全局风格锚定提示词的对话消息。"""
    user_input = _build_global_style_gen_input(style_config)
    if ref_style_description:
        user_input += f"\n\n参考图片的视觉风格分析：\n{ref_style_description}"
    return [
        {"role": "system", "content": GLOBAL_STYLE_GEN_PROMPT},
        {"role": "user", "content": user_input},
    ]


def get_image_prompt(page_title: str, page_content: str, relationship: str,
                     style_config: dict, is_cover: bool = False, is_ending: bool = False) -> str:
    aspect = style_config.get("aspect_ratio", "16:9")
    parts = [f"生成一张 {aspect} 比例的 PPT 页面图片。\n"]

    global_style = style_config.get("global_style_prompt")
    if global_style:
        parts.append(f"【全局视觉规范 — 必须严格遵守】\n{global_style}\n\n")

    if is_cover:
        parts.append("这是封面页，需要大标题居中，简洁大气。\n")
    elif is_ending:
        parts.append("这是结尾页/感谢页，简洁有力。\n")

    parts.append(f"页面标题：{page_title}\n")
    parts.append(f"页面内容：{page_content}\n")

    visual_hint = RELATIONSHIP_VISUAL_MAP.get(relationship)
    if visual_hint:
        parts.append(f"\n内容关系为「{relationship}」，视觉呈现要求：{visual_hint}\n")

    if not global_style:
        if style_config.get("style_description"):
            parts.append(f"\n风格要求：{style_config['style_description']}\n")
        preset = style_config.get("preset")
        if preset:
            preset_styles = {
                "business": "商务专业风格，深蓝色系，简洁大方",
                "academic": "学术风格，白底黑字，严谨规范",
                "tech": "科技风格，深色渐变背景，霓虹蓝/紫点缀",
                "minimal": "极简风格，大量留白，少量色彩",
                "creative": "创意风格，色彩丰富，自由排版",
                "education": "教育风格，温暖色调，清晰易读",
            }
            parts.append(f"\n预设风格：{preset_styles.get(preset, preset)}\n")

    parts.append("\n要求：所有文字必须清晰可辨，不能有乱码。排版专业美观。")
    return "".join(parts)


BACKGROUND_TEMPLATE_PROMPT = """\
生成一张 {aspect_ratio} 比例的 PPT 背景模板图片。

要求：
1. 这是一张纯背景模板，**不包含任何文字、标题、正文内容**
2. 可以包含装饰性元素：渐变色块、几何图形、线条、光效、纹理等
3. 页面上方留出标题区域（约占 15% 高度），中间和下方留出内容区域
4. 装饰元素不要遮挡内容区域，集中在边角和边缘
5. 整体风格统一、专业、美观

{style_instructions}

重要：绝对不要在图片上放任何文字！只要背景和装饰元素。
"""


def get_background_template_prompt(style_config: dict) -> str:
    aspect = style_config.get("aspect_ratio", "16:9")
    lines: list[str] = []

    global_style = style_config.get("global_style_prompt")
    if global_style:
        lines.append(f"【全局视觉规范 — 必须严格遵守】\n{global_style}")

    if style_config.get("style_description"):
        lines.append(f"风格要求：{style_config['style_description']}")

    preset = style_config.get("preset")
    if preset:
        preset_styles = {
            "business": "商务专业风格，深蓝色系，简洁大方",
            "academic": "学术风格，浅灰白底，严谨规范",
            "tech": "科技风格，深色渐变背景，霓虹蓝/紫点缀",
            "minimal": "极简风格，大量留白，少量色彩",
            "creative": "创意风格，色彩丰富，几何装饰",
            "education": "教育风格，温暖色调，柔和渐变",
        }
        lines.append(f"预设风格：{preset_styles.get(preset, preset)}")

    if not lines:
        lines.append("请设计一套专业美观的背景模板，配色协调，适合商务演示。")

    return BACKGROUND_TEMPLATE_PROMPT.format(
        aspect_ratio=aspect,
        style_instructions="\n".join(lines),
    )


CONTENT_LAYER_PROMPT = """\
你是一名专业的 PPT 内容排版设计师。

我会提供一张 PPT 背景模板图片。请在这张背景上排版以下内容，生成完整的 PPT 页面：

{page_type_hint}
页面标题：{title}
页面内容：{content}
{relationship_hint}

排版要求：
1. **必须保留背景模板的所有元素**（背景色、渐变、装饰图形等），不要修改背景
2. 文字颜色要与背景形成良好对比，确保清晰可读
3. 标题放在页面上方，字号大、加粗
4. 内容区域合理排版，使用适当的层次结构
5. 可以添加图标、图表、示意图来增强信息表达
6. 所有文字必须精确渲染，不允许出现乱码或模糊文字

{style_hint}
"""


def get_content_layer_prompt(page_title: str, page_content: str, relationship: str,
                             style_config: dict, is_cover: bool = False,
                             is_ending: bool = False) -> str:
    if is_cover:
        page_type_hint = "这是封面页，需要大标题居中，副标题在下方，简洁大气。"
    elif is_ending:
        page_type_hint = "这是结尾页/感谢页，简洁有力，可以有简短的总结语。"
    else:
        page_type_hint = ""

    visual_hint = RELATIONSHIP_VISUAL_MAP.get(relationship)
    relationship_hint = (
        f"内容关系为「{relationship}」，视觉呈现要求：{visual_hint}"
        if visual_hint else ""
    )

    global_style = style_config.get("global_style_prompt", "")
    style_hint = f"【全局视觉规范】\n{global_style}" if global_style else ""

    return CONTENT_LAYER_PROMPT.format(
        page_type_hint=page_type_hint,
        title=page_title,
        content=page_content,
        relationship_hint=relationship_hint,
        style_hint=style_hint,
    )


REPLACE_TEXT_PROMPT = """你是一名 PPT 页面编辑专家。
用户要求在现有 PPT 页面图片上进行文字替换：
- 将「{old_text}」替换为「{new_text}」
{extra}
请生成替换后的完整页面图片，保持其他所有元素不变，仅修改指定文字。
风格、排版、配色必须与原图保持一致。"""


def get_replace_text_prompt(old_text: str, new_text: str, extra_prompt: str = "") -> str:
    extra = f"- 额外要求：{extra_prompt}" if extra_prompt else ""
    return REPLACE_TEXT_PROMPT.format(old_text=old_text, new_text=new_text, extra=extra)


MASK_EDIT_PROMPT = """你是一名 PPT 页面编辑专家。
用户在 PPT 页面图片上框选了一个区域进行局部重绘。
区域位置：左上角 ({x}, {y})，宽度 {w}，高度 {h}（像素坐标）。

用户要求：{prompt}

请仅重绘该区域内容，保持区域外的所有元素完全不变。
确保重绘内容与周围风格协调一致。"""


def get_mask_edit_prompt(region: dict, prompt: str) -> str:
    return MASK_EDIT_PROMPT.format(
        x=region.get("x", 0), y=region.get("y", 0),
        w=region.get("width", 0), h=region.get("height", 0),
        prompt=prompt,
    )


DOCUMENT_ANALYSIS_PROMPT = """你是一名文档分析专家。请分析以下文档内容，提取关键信息用于生成演示文稿。

输出 JSON 格式：
{
  "title": "文档标题/主题",
  "summary": "200字以内的内容摘要",
  "key_points": ["关键要点1", "关键要点2", ...],
  "suggested_outline": [
    {"title": "建议的章节标题", "points": ["要点1", "要点2"], "relationship": "parallel"}
  ],
  "total_pages_suggestion": 10
}

确保提取所有重要信息，不遗漏关键数据和结论。"""
