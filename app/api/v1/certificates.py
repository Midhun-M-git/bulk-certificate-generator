import os
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.certificate import Certificate, CertificateStatus
from app.schemas.certificate import CertificateResponse
from app.config import settings

router = APIRouter(prefix="/certificates", tags=["Certificates"])


def _to_response(cert: Certificate) -> CertificateResponse:
    download_url = f"{settings.API_V1_PREFIX}/certificates/{cert.id}/download" if cert.status == CertificateStatus.SUCCESS else None
    preview_url = f"{settings.API_V1_PREFIX}/certificates/{cert.id}/preview" if cert.status == CertificateStatus.SUCCESS else None

    return CertificateResponse(
        id=cert.id,
        job_id=cert.job_id,
        certificate_number=cert.certificate_number,
        recipient_name=cert.recipient_name,
        recipient_email=cert.recipient_email,
        status=cert.status.value if hasattr(cert.status, "value") else str(cert.status),
        download_url=download_url,
        preview_url=preview_url,
        file_size_bytes=cert.file_size_bytes,
        failure_reason=cert.failure_reason,
        created_at=cert.created_at.isoformat() if cert.created_at else None,
        generated_at=cert.generated_at.isoformat() if cert.generated_at else None,
    )


@router.get(
    "/{certificate_id}",
    response_model=CertificateResponse,
    summary="Get individual certificate details",
    description="Returns metadata and current generation status for a specific certificate.",
)
def get_certificate(
    certificate_id: str,
    db: Session = Depends(get_db),
):
    cert = db.query(Certificate).filter(Certificate.id == certificate_id).first()
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate with ID '{certificate_id}' was not found.",
        )
    return _to_response(cert)


@router.get(
    "/{certificate_id}/download",
    summary="Download individual certificate PDF",
    description="Downloads the generated PDF certificate as a file attachment.",
)
def download_certificate(
    certificate_id: str,
    db: Session = Depends(get_db),
):
    cert = db.query(Certificate).filter(Certificate.id == certificate_id).first()
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate with ID '{certificate_id}' was not found.",
        )

    if cert.status != CertificateStatus.SUCCESS or not cert.file_path or not os.path.isfile(cert.file_path):
        if cert.status == CertificateStatus.FAILED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Certificate generation failed: {cert.failure_reason}",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Certificate is not ready for download. Current status: {cert.status.value}",
        )

    safe_name = "".join(c for c in cert.recipient_name if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
    filename = f"{safe_name}_{cert.certificate_number}.pdf"

    return FileResponse(
        path=cert.file_path,
        media_type="application/pdf",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/{certificate_id}/preview",
    summary="Preview individual certificate PDF inline",
    description="Serves the PDF with inline content disposition so browsers can render it directly.",
)
def preview_certificate(
    certificate_id: str,
    db: Session = Depends(get_db),
):
    cert = db.query(Certificate).filter(Certificate.id == certificate_id).first()
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate with ID '{certificate_id}' was not found.",
        )

    if cert.status != CertificateStatus.SUCCESS or not cert.file_path or not os.path.isfile(cert.file_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Certificate is not ready for preview. Current status: {cert.status.value}",
        )

    return FileResponse(
        path=cert.file_path,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline"},
    )
