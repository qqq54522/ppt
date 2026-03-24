import uuid
from datetime import datetime, timezone
from . import db


class ReferenceFile(db.Model):
    __tablename__ = "reference_files"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = db.Column(db.String(36), db.ForeignKey("projects.id"), nullable=True)
    filename = db.Column(db.String(500), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(20), default="")
    analysis_result = db.Column(db.JSON, default=dict)
    status = db.Column(db.String(20), default="uploaded")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "filename": self.filename,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "analysis_result": self.analysis_result,
            "status": self.status,
        }
