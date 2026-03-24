import uuid
from datetime import datetime, timezone
from . import db


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(255), default="Untitled")
    creation_type = db.Column(db.String(20), nullable=False)  # upload / idea / outline
    idea_prompt = db.Column(db.Text, default="")
    outline_text = db.Column(db.Text, default="")
    document_analysis = db.Column(db.JSON, default=dict)
    style_config = db.Column(db.JSON, default=dict)
    status = db.Column(db.String(20), default="created")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    pages = db.relationship("Page", backref="project", lazy=True,
                            cascade="all, delete-orphan", order_by="Page.page_number")
    tasks = db.relationship("Task", backref="project", lazy=True, cascade="all, delete-orphan")
    reference_files = db.relationship("ReferenceFile", backref="project", lazy=True,
                                      cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "creation_type": self.creation_type,
            "idea_prompt": self.idea_prompt,
            "outline_text": self.outline_text,
            "document_analysis": self.document_analysis,
            "style_config": self.style_config,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "pages": [p.to_dict() for p in self.pages],
        }
