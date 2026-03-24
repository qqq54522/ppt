from flask import Blueprint, request
from models import db
from models.page import Page
from utils.response import success, error

page_bp = Blueprint("pages", __name__, url_prefix="/api/projects/<project_id>/pages")


@page_bp.route("", methods=["GET"])
def list_pages(project_id):
    pages = Page.query.filter_by(project_id=project_id).order_by(Page.page_number).all()
    return success([p.to_dict() for p in pages])


@page_bp.route("", methods=["POST"])
def create_page(project_id):
    data = request.get_json() or {}
    max_num = db.session.query(db.func.max(Page.page_number)).filter_by(project_id=project_id).scalar() or 0
    page = Page(
        project_id=project_id,
        page_number=max_num + 1,
        title=data.get("title", "新页面"),
        content=data.get("content", ""),
        relationship_type=data.get("relationship_type", "none"),
    )
    db.session.add(page)
    db.session.commit()
    return success(page.to_dict())


@page_bp.route("/<page_id>", methods=["PUT"])
def update_page(project_id, page_id):
    page = db.session.get(Page, page_id)
    if not page or page.project_id != project_id:
        return error("Page not found", 404)
    data = request.get_json() or {}
    for field in ("title", "content", "relationship_type", "page_number"):
        if field in data:
            setattr(page, field, data[field])
    db.session.commit()
    return success(page.to_dict())


@page_bp.route("/<page_id>", methods=["DELETE"])
def delete_page(project_id, page_id):
    page = db.session.get(Page, page_id)
    if not page or page.project_id != project_id:
        return error("Page not found", 404)
    db.session.delete(page)
    db.session.commit()
    return success(message="Deleted")


@page_bp.route("/<page_id>/regenerate", methods=["POST"])
def regenerate_page_image(project_id, page_id):
    """重新生成页面。支持 layer 参数选择重新生成的层。

    POST body (可选):
      - layer: "all" (默认) | "visual" | "text"
        - all: 重新生成视觉层+文字层（完整重做）
        - visual: 仅重新生成视觉层图片，保留现有文字层 HTML
        - text: 仅重新生成文字层 HTML，保留现有视觉层图片
    """
    from services.ai_service import get_ai_service
    page = db.session.get(Page, page_id)
    if not page or page.project_id != project_id:
        return error("Page not found", 404)

    data = request.get_json(silent=True) or {}
    layer = data.get("layer", "all")

    ai = get_ai_service()
    project = page.project

    if layer == "visual":
        image_path = ai.regenerate_visual_only(project, page)
    elif layer == "text":
        image_path = ai.regenerate_text_only(project, page)
    else:
        image_path = ai.generate_slide_image(project, page)

    if page.image_path:
        versions = page.image_versions or []
        versions.append(page.image_path)
        page.image_versions = versions

    page.image_path = image_path
    page.status = "generated"
    db.session.commit()
    return success(page.to_dict())


@page_bp.route("/<page_id>/replace-text", methods=["POST"])
def replace_text(project_id, page_id):
    from services.ai_service import get_ai_service
    page = db.session.get(Page, page_id)
    if not page or page.project_id != project_id:
        return error("Page not found", 404)
    if not page.image_path:
        return error("No image to edit", 400)

    data = request.get_json() or {}
    old_text = data.get("old_text", "")
    new_text = data.get("new_text", "")
    extra_prompt = data.get("extra_prompt", "")

    ai = get_ai_service()
    new_image_path = ai.replace_text_in_slide(page, old_text, new_text, extra_prompt)

    versions = page.image_versions or []
    versions.append(page.image_path)
    page.image_versions = versions
    page.image_path = new_image_path
    db.session.commit()
    return success(page.to_dict())


@page_bp.route("/<page_id>/mask-edit", methods=["POST"])
def mask_edit(project_id, page_id):
    from services.ai_service import get_ai_service
    page = db.session.get(Page, page_id)
    if not page or page.project_id != project_id:
        return error("Page not found", 404)
    if not page.image_path:
        return error("No image to edit", 400)

    data = request.get_json() or {}
    region = data.get("region", {})
    prompt = data.get("prompt", "")

    ai = get_ai_service()
    try:
        new_image_path = ai.mask_edit_slide(page, region, prompt)
    except RuntimeError as e:
        return error(str(e), 502)

    versions = page.image_versions or []
    versions.append(page.image_path)
    page.image_versions = versions
    page.image_path = new_image_path
    db.session.commit()
    return success(page.to_dict())


@page_bp.route("/<page_id>/render-html", methods=["POST"])
def render_html(project_id, page_id):
    """用当前 html_content 重新渲染截图（前端编辑 HTML 后调用）。

    方案C：优先使用页面独立的视觉层图片作为背景，回退到全局底图模板。
    """
    from services.render_service import render_slide_for_project
    import os

    page = db.session.get(Page, page_id)
    if not page or page.project_id != project_id:
        return error("Page not found", 404)

    data = request.get_json() or {}
    html = data.get("html_content", page.html_content or "")
    if not html.strip():
        return error("HTML content is empty", 400)

    page.html_content = html

    project = page.project
    bg_path = page.visual_image_path or (project.style_config or {}).get("background_template")
    filename = f"page_{page.page_number}_{os.urandom(4).hex()}.png"

    try:
        rel_path = render_slide_for_project(
            html, project.id, filename, bg_path=bg_path,
        )
    except Exception as e:
        return error(f"渲染失败：{str(e)[:200]}", 500)

    if page.image_path:
        versions = page.image_versions or []
        versions.append(page.image_path)
        page.image_versions = versions

    page.image_path = rel_path
    page.status = "generated"
    db.session.commit()
    return success(page.to_dict())


@page_bp.route("/reorder", methods=["PUT"])
def reorder_pages(project_id):
    data = request.get_json() or {}
    order = data.get("order", [])
    for i, page_id in enumerate(order):
        page = db.session.get(Page, page_id)
        if page and page.project_id == project_id:
            page.page_number = i + 1
    db.session.commit()
    pages = Page.query.filter_by(project_id=project_id).order_by(Page.page_number).all()
    return success([p.to_dict() for p in pages])
