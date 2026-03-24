import os
import zipfile
import logging
import gc

from PIL import Image
from reportlab.lib.pagesizes import landscape
from reportlab.pdfgen import canvas as pdf_canvas

from utils.path_utils import UPLOAD_FOLDER

logger = logging.getLogger(__name__)

PDF_W = 1920
PDF_H = 1080


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


def _downscale_for_pdf(src_path: str, out_path: str) -> str:
    """Downscale a single image to 1920x1080 RGB JPEG, freeing memory immediately."""
    img = Image.open(src_path)
    if img.mode in ("RGBA", "P", "LA"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        if "A" in img.mode:
            bg.paste(img, mask=img.split()[-1])
        else:
            bg.paste(img)
        img.close()
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    if img.width > PDF_W or img.height > PDF_H:
        img.thumbnail((PDF_W, PDF_H), Image.LANCZOS)

    img.save(out_path, "JPEG", quality=88)
    img.close()
    gc.collect()
    return out_path


def export_as_pdf(project) -> str | None:
    paths = _get_page_image_paths(project)
    if not paths:
        return None

    export_dir = _ensure_export_dir(project.id)
    pdf_path = os.path.join(export_dir, "slides.pdf")

    try:
        page_size = landscape((PDF_W, PDF_H))
        c = pdf_canvas.Canvas(pdf_path, pagesize=page_size)

        for i, src in enumerate(paths):
            tmp_jpg = os.path.join(export_dir, f"_tmp_{i:02d}.jpg")
            try:
                _downscale_for_pdf(src, tmp_jpg)
                c.drawImage(tmp_jpg, 0, 0, width=PDF_W, height=PDF_H)
                c.showPage()
            finally:
                if os.path.exists(tmp_jpg):
                    os.remove(tmp_jpg)
            gc.collect()

        c.save()
    except Exception as e:
        logger.error("PDF export failed: %s", e)
        return None

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
