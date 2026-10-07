import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Enum, Text
from sqlalchemy.orm import relationship
from app.database import Base


class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    issuer_name = Column(String(255), nullable=False)
    issue_date = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    
    status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False, index=True)
    total_count = Column(Integer, default=0, nullable=False)
    processed_count = Column(Integer, default=0, nullable=False)
    success_count = Column(Integer, default=0, nullable=False)
    failed_count = Column(Integer, default=0, nullable=False)
    
    zip_path = Column(String(500), nullable=True)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    certificates = relationship(
        "Certificate", 
        back_populates="job", 
        cascade="all, delete-orphan",
        order_by="Certificate.created_at"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "issuer_name": self.issuer_name,
            "issue_date": self.issue_date,
            "description": self.description,
            "status": self.status.value if isinstance(self.status, JobStatus) else self.status,
            "total_count": self.total_count,
            "processed_count": self.processed_count,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "progress_percentage": round((self.processed_count / self.total_count * 100), 1) if self.total_count > 0 else 0,
            "has_zip": bool(self.zip_path),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
