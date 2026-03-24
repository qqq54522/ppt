import os
import sys
import logging
from pathlib import Path

from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path, override=True)

from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from config import Config
from models import db


def _safe_add_column(app: Flask, table: str, column: str, col_type: str):
    """Add a column if it doesn't already exist (SQLite-safe)."""
    import sqlite3
    db_path = app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", "")
    try:
        conn = sqlite3.connect(db_path)
        cols = [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        if column not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            conn.commit()
        conn.close()
    except Exception:
        pass


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    db_path = os.path.join(app.instance_path, "database.db")
    os.makedirs(app.instance_path, exist_ok=True)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

    upload_folder = app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)

    origins = app.config["CORS_ORIGINS"]
    if origins == "*":
        CORS(app, resources={r"/api/*": {"origins": "*"}})
    else:
        CORS(app, resources={r"/api/*": {"origins": [o.strip() for o in origins.split(",")]}})

    db.init_app(app)
    Migrate(app, db)

    logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    from controllers.project_controller import project_bp
    from controllers.page_controller import page_bp
    from controllers.file_controller import file_bp
    from controllers.export_controller import export_bp

    app.register_blueprint(project_bp)
    app.register_blueprint(page_bp)
    app.register_blueprint(file_bp)
    app.register_blueprint(export_bp)

    with app.app_context():
        db.create_all()
        _safe_add_column(app, "pages", "html_content", "TEXT DEFAULT ''")
        _safe_add_column(app, "pages", "visual_image_path", "VARCHAR(500) DEFAULT ''")

    @app.route("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("BACKEND_PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_ENV") == "development")
