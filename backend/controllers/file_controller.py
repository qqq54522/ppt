import os
import uuid
from flask import Blueprint, request, send_from_directory, current_app
from models import db
from models.reference_file import ReferenceFile
from utils.response import success, error
from utils.path_utils import allowed_file, get_project_folder

file_bp = Blueprint("files", __name__)


def _safe_filename(original: str) -> str:
    """Generate a UUID-based filename preserving the original extension."""
    ext = original.rsplit(".", 1)[1].lower() if "." in original else ""
    return f"{uuid.uuid4().hex[:12]}.{ext}" if ext else uuid.uuid4().hex[:12]


@file_bp.route("/api/files/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return error("No file provided", 400)

    file = request.files["file"]
    if not file.filename:
        return error("Empty filename", 400)

    project_id = request.form.get("project_id")
    all_ext = current_app.config["ALLOWED_EXTENSIONS"] | current_app.config["ALLOWED_IMAGE_EXTENSIONS"]
    if not allowed_file(file.filename, all_ext):
        return error("File type not allowed", 400)

    safe_name = _safe_filename(file.filename)
    ext = safe_name.rsplit(".", 1)[1].lower() if "." in safe_name else ""

    if project_id:
        folder = get_project_folder(project_id)
        relative_dir = os.path.join("projects", project_id)
    else:
        folder = os.path.join(current_app.config["UPLOAD_FOLDER"], "global")
        os.makedirs(folder, exist_ok=True)
        relative_dir = "global"

    filepath = os.path.join(folder, safe_name)
    file.save(filepath)

    relative_path = os.path.join(relative_dir, safe_name).replace("\\", "/")

    ref = ReferenceFile(
        project_id=project_id,
        filename=file.filename,
        file_path=relative_path,
        file_type=ext,
    )
    db.session.add(ref)
    db.session.commit()
    return success(ref.to_dict(), code=201)


@file_bp.route("/api/files/<ref_id>/analyze", methods=["POST"])
def analyze_file(ref_id):
    ref = db.session.get(ReferenceFile, ref_id)
    if not ref:
        return error("File not found", 404)

    abs_path = os.path.join(current_app.config["UPLOAD_FOLDER"], ref.file_path)
    from services.ai_service import get_ai_service
    ai = get_ai_service()
    result = ai.analyze_document(abs_path, ref.file_type)

    ref.analysis_result = result
    ref.status = "analyzed"
    db.session.commit()
    return success(ref.to_dict())


@file_bp.route("/api/files/<ref_id>", methods=["GET"])
def get_file_info(ref_id):
    ref = db.session.get(ReferenceFile, ref_id)
    if not ref:
        return error("File not found", 404)
    return success(ref.to_dict())


@file_bp.route("/api/files", methods=["GET"])
def list_files():
    project_id = request.args.get("project_id")
    q = ReferenceFile.query
    if project_id:
        q = q.filter_by(project_id=project_id)
    files = q.order_by(ReferenceFile.created_at.desc()).all()
    return success([f.to_dict() for f in files])


@file_bp.route("/uploads/<path:filepath>", methods=["GET"])
def serve_upload(filepath):
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    return send_from_directory(upload_dir, filepath)
