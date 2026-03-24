import os
from flask import Blueprint, send_file
from models import db
from models.project import Project
from utils.response import success, error

export_bp = Blueprint("export", __name__, url_prefix="/api/projects/<project_id>/export")


@export_bp.route("/pdf", methods=["POST"])
def export_pdf(project_id):
    from services.export_service import export_as_pdf
    project = db.session.get(Project, project_id)
    if not project:
        return error("Project not found", 404)

    pdf_path = export_as_pdf(project)
    if not pdf_path or not os.path.exists(pdf_path):
        return error("Export failed", 500)
    return send_file(pdf_path, as_attachment=True,
                     download_name=f"{project.title or 'slides'}.pdf")


@export_bp.route("/images", methods=["POST"])
def export_images_zip(project_id):
    from services.export_service import export_as_images_zip
    project = db.session.get(Project, project_id)
    if not project:
        return error("Project not found", 404)

    zip_path = export_as_images_zip(project)
    if not zip_path or not os.path.exists(zip_path):
        return error("Export failed", 500)
    return send_file(zip_path, as_attachment=True,
                     download_name=f"{project.title or 'slides'}.zip")
