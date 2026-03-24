import os
import zipfile
import logging
from pathlib import Path

import img2pdf
from PIL import Image

from utils.path_utils import UPLOAD_FOLDER

logger = logging.getLogger(__name__)


def _get_page_image_paths(project) -> list[str]:
    paths = []
    for page in sorted(project.pages, key=lambda p: p.page_number):
        if page.image_path:
            abs_path = os.path.join(UPLOAD_FOLDER, page.image_path)
            if os.path.exists(abs_path):
                paths.append(abs_path)
    return paths


def _ensure_export_dir(project_id: str) -> str:
    export_dir = os.path.join(UPLOAD_FOLDER, "exports", project_id)
    os.makedirs(export_dir, exist_ok=True)
    return export_dir


def export_as_pdf(project) -> str | None:
    paths = _get_page_image_paths(project)
    if not paths:
        return None

    export_dir = _ensure_export_dir(project.id)
    pdf_path = os.path.join(export_dir, "slides.pdf")

    png_paths = []
    for p in paths:
        img = Image.open(p)
        if img.mode == "RGBA":
            rgb = Image.new("RGB", img.size, (255, 255, 255))
            rgb.paste(img, mask=img.split()[3])
            new_path = p + ".conv.jpg"
            rgb.save(new_path, "JPEG", quality=95)
            png_paths.append(new_path)
        else:
            png_paths.append(p)

    try:
        with open(pdf_path, "wb") as f:
            f.write(img2pdf.convert(png_paths))
    except Exception as e:
        logger.error("PDF export failed: %s", e)
        return None

    for p in png_paths:
        if p.endswith(".conv.jpg"):
            os.remove(p)

    return pdf_path


def export_as_images_zip(project) -> str | None:
    paths = _get_page_image_paths(project)
    if not paths:
        return None

    export_dir = _ensure_export_dir(project.id)
    zip_path = os.path.join(export_dir, "slides.zip")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, p in enumerate(paths):
            ext = os.path.splitext(p)[1] or ".png"
            zf.write(p, f"slide_{i+1:02d}{ext}")

    return zip_path
