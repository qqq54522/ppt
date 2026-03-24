import uuid
from datetime import datetime, timezone
from . import db


class Page(db.Model):
    __tablename__ = "pages"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = db.Column(db.String(36), db.ForeignKey("projects.id"), nullable=False)
    page_number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(500), default="")
    content = db.Column(db.Text, default="")
    relationship_type = db.Column(db.String(30), default="none")
    image_path = db.Column(db.String(500), default="")
    image_versions = db.Column(db.JSON, default=list)
    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "page_number": self.page_number,
            "title": self.title,
            "content": self.content,
            "relationship_type": self.relationship_type,
            "image_path": self.image_path,
            "image_versions": self.image_versions or [],
            "status": self.status,
        }
