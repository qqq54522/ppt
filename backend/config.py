import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = "sqlite:///database.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://www.lemonapi.ai/v1")
    TEXT_MODEL = os.getenv("TEXT_MODEL", "[V]gemini-3.1-pro-preview")
    IMAGE_MODEL = os.getenv("IMAGE_MODEL", "[V]gemini-3-flash-preview")

    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 50 * 1024 * 1024))
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
    ALLOWED_EXTENSIONS = {"pdf", "docx", "doc", "txt", "md", "pptx", "xlsx", "csv"}
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

    ARK_API_KEY = os.getenv("ARK_API_KEY", "")
    ARK_API_BASE = os.getenv("ARK_API_BASE", "https://ark.cn-beijing.volces.com/api/v3")
    ARK_IMAGE_MODEL = os.getenv("ARK_IMAGE_MODEL", "doubao-seedream-5-0-260128")
    # 为 true 时，生成整页 / 替换文字等文生图也会优先走火山 Ark（豆包），便于在控制台看到调用
    USE_ARK_FOR_SLIDE_IMAGES = os.getenv("USE_ARK_FOR_SLIDE_IMAGES", "").lower() in (
        "1",
        "true",
        "yes",
    )

    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
    MAX_IMAGE_WORKERS = int(os.getenv("MAX_IMAGE_WORKERS", 4))
    BACKEND_PORT = int(os.getenv("BACKEND_PORT", 5000))
