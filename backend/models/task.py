import uuid
from datetime import datetime, timezone
from . import db


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = db.Column(db.String(36), db.ForeignKey("projects.id"), nullable=False)
    task_type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default="pending")
    progress = db.Column(db.Float, default=0.0)
    result = db.Column(db.JSON, default=dict)
    error = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "task_type": self.task_type,
            "status": self.status,
            "progress": self.progress,
            "result": self.result,
            "error": self.error,
        }
