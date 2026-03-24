import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, "uploads")


def get_project_folder(project_id: str) -> str:
    folder = os.path.join(UPLOAD_FOLDER, "projects", project_id)
    os.makedirs(folder, exist_ok=True)
    return folder


def get_project_images_folder(project_id: str) -> str:
    folder = os.path.join(get_project_folder(project_id), "images")
    os.makedirs(folder, exist_ok=True)
    return folder


def get_upload_temp_folder() -> str:
    folder = os.path.join(UPLOAD_FOLDER, "temp")
    os.makedirs(folder, exist_ok=True)
    return folder


def allowed_file(filename: str, allowed_ext: set) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_ext
