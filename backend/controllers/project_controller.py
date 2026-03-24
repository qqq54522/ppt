from flask import Blueprint, request
from models import db
from models.project import Project
from models.page import Page
from models.task import Task
from utils.response import success, error
from services import task_manager

project_bp = Blueprint("projects", __name__, url_prefix="/api/projects")


@project_bp.route("", methods=["POST"])
def create_project():
    data = request.get_json() or {}
    creation_type = data.get("creation_type", "idea")
    if creation_type not in ("upload", "idea", "outline"):
        return error("Invalid creation_type", 400)

    project = Project(
        title=data.get("title", "Untitled"),
        creation_type=creation_type,
        idea_prompt=data.get("idea_prompt", ""),
        outline_text=data.get("outline_text", ""),
        style_config=data.get("style_config", {}),
    )
    db.session.add(project)
    db.session.commit()
    return success(project.to_dict(), code=201)


@project_bp.route("", methods=["GET"])
def list_projects():
    projects = Project.query.order_by(Project.created_at.desc()).all()
    return success([p.to_dict() for p in projects])


@project_bp.route("/<project_id>", methods=["GET"])
def get_project(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return error("Project not found", 404)
    return success(project.to_dict())


@project_bp.route("/<project_id>", methods=["PUT"])
def update_project(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return error("Project not found", 404)
    data = request.get_json() or {}
    for field in ("title", "idea_prompt", "outline_text", "style_config", "document_analysis", "status"):
        if field in data:
            setattr(project, field, data[field])
    db.session.commit()
    return success(project.to_dict())


@project_bp.route("/<project_id>", methods=["DELETE"])
def delete_project(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return error("Project not found", 404)
    db.session.delete(project)
    db.session.commit()
    return success(message="Deleted")


@project_bp.route("/<project_id>/generate/outline", methods=["POST"])
def generate_outline(project_id):
    from services.ai_service import get_ai_service
    project = db.session.get(Project, project_id)
    if not project:
        return error("Project not found", 404)

    ai = get_ai_service()
    result = ai.generate_outline(project)

    Page.query.filter_by(project_id=project_id).delete()
    for i, item in enumerate(result.get("pages", [])):
        page = Page(
            project_id=project_id,
            page_number=i + 1,
            title=item.get("title", ""),
            content=item.get("content", ""),
            relationship_type=item.get("relationship", "none"),
        )
        db.session.add(page)

    project.outline_text = result.get("outline_text", project.outline_text)
    project.title = result.get("title", project.title)
    project.status = "outline_ready"
    db.session.commit()
    return success(project.to_dict())


@project_bp.route("/<project_id>/generate/images", methods=["POST"])
def generate_images(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return error("Project not found", 404)

    data = request.get_json() or {}
    page_ids = data.get("page_ids")

    task = Task(project_id=project_id, task_type="generate_images")
    db.session.add(task)
    db.session.commit()

    from flask import current_app
    from services.ai_service import generate_images_task
    task_manager.submit_task(current_app._get_current_object(), task.id,
                            generate_images_task, project_id, page_ids)
    return success({"task_id": task.id}, code=202)


@project_bp.route("/<project_id>/tasks/<task_id>", methods=["GET"])
def get_task_status(project_id, task_id):
    task = db.session.get(Task, task_id)
    if not task or task.project_id != project_id:
        return error("Task not found", 404)
    return success(task.to_dict())
