from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.recipient import RecipientInput
from app.schemas.certificate import CertificateResponse


class JobCreateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Full-Stack Web Development Bootcamp",
                "issuer_name": "DevAcademy Global",
                "issue_date": "October 7, 2026",
                "description": "for outstanding performance and completion of the 12-week intensive program",
                "recipients": [
                    {"name": "Alice Johnson", "email": "alice@example.com"},
                    {"name": "Bob Smith", "email": "bob@example.com"},
                    {"name": "Charlie Brown", "email": "charlie@example.com"}
                ]
            }
        }
    )

    title: str = Field(..., min_length=1, max_length=255, description="Event or Course title")
    issuer_name: str = Field(..., min_length=1, max_length=255, description="Name of issuing institution or organization")
    issue_date: str = Field(..., min_length=1, max_length=50, description="Date of issuance")
    description: Optional[str] = Field(None, description="Certificate subtitle or achievement description")
    recipients: List[RecipientInput] = Field(..., min_length=1, description="List of certificate recipients")


class JobCreatedResponse(BaseModel):
    job_id: str
    status: str
    message: str
    total_recipients: int
    status_url: str


class JobSummaryResponse(BaseModel):
    id: str
    title: str
    issuer_name: str
    issue_date: str
    description: Optional[str] = None
    status: str
    total_count: int
    processed_count: int
    success_count: int
    failed_count: int
    progress_percentage: float
    has_zip: bool
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class JobDetailResponse(JobSummaryResponse):
    zip_download_url: Optional[str] = None
    certificates: List[CertificateResponse] = []
