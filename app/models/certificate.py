import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Enum, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class CertificateStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class Certificate(Base):
    __tablename__ = "certificates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    certificate_number = Column(String(50), unique=True, nullable=False, index=True)
    
    recipient_name = Column(String(255), nullable=False)
    recipient_email = Column(String(255), nullable=True)
    metadata_json = Column(Text, nullable=True)
    
    status = Column(Enum(CertificateStatus), default=CertificateStatus.PENDING, nullable=False, index=True)
    file_path = Column(String(500), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    failure_reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    generated_at = Column(DateTime, nullable=True)

    job = relationship("Job", back_populates="certificates")

    def to_dict(self):
        return {
            "id": self.id,
            "job_id": self.job_id,
            "certificate_number": self.certificate_number,
            "recipient_name": self.recipient_name,
            "recipient_email": self.recipient_email,
            "status": self.status.value if isinstance(self.status, CertificateStatus) else self.status,
            "file_size_bytes": self.file_size_bytes,
            "failure_reason": self.failure_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
        }
