from typing import Optional
from pydantic import BaseModel, ConfigDict


class CertificateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    certificate_number: str
    recipient_name: str
    recipient_email: Optional[str] = None
    status: str
    download_url: Optional[str] = None
    preview_url: Optional[str] = None
    file_size_bytes: Optional[int] = None
    failure_reason: Optional[str] = None
    created_at: Optional[str] = None
    generated_at: Optional[str] = None
