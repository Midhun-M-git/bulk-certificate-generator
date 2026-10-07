import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.job import Job, JobStatus
from app.models.certificate import Certificate, CertificateStatus
from app.schemas.job import JobCreateRequest, JobCreatedResponse, JobSummaryResponse, JobDetailResponse
from app.schemas.certificate import CertificateResponse
from app.services.job_service import job_service
from app.config import settings

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def _build_certificate_response(cert: Certificate) -> CertificateResponse:
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


@router.post(
    "",
    response_model=JobCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a bulk certificate generation job",
    description="Accepts event details and a list of recipients. Validates recipient data, queues background generation, and immediately returns the job tracking identifier.",
)
def create_job(
    request: JobCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if len(request.recipients) > settings.MAX_RECIPIENTS_PER_BATCH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch size exceeds maximum allowed of {settings.MAX_RECIPIENTS_PER_BATCH} recipients.",
        )

    # Create job in database and record initial recipient states
    job = job_service.create_generation_job(db, request)

    # If there are pending certificates to generate, queue the background worker
    if job.status != JobStatus.FAILED:
        background_tasks.add_task(job_service.process_job, job.id)

    status_url = f"{settings.API_V1_PREFIX}/jobs/{job.id}"
    return JobCreatedResponse(
        job_id=job.id,
        status=job.status.value,
        message="Bulk certificate generation job accepted and scheduled for background processing.",
        total_recipients=job.total_count,
        status_url=status_url,
    )


@router.get(
    "",
    response_model=List[JobSummaryResponse],
    summary="List recent certificate generation jobs",
    description="Returns a paginated list of recent bulk generation jobs and their execution summaries.",
)
def list_jobs(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    jobs = (
        db.query(Job)
        .order_by(Job.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [job.to_dict() for job in jobs]


@router.get(
    "/{job_id}",
    response_model=JobDetailResponse,
    summary="Check job status, progress, and recipient results",
    description="Returns real-time progress counters, execution status, and individual recipient certificate statuses.",
)
def get_job(
    job_id: str,
    db: Session = Depends(get_db),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate job with ID '{job_id}' not found.",
        )

    certs = (
        db.query(Certificate)
        .filter(Certificate.job_id == job_id)
        .order_by(Certificate.created_at)
        .all()
    )

    cert_responses = [_build_certificate_response(c) for c in certs]
    zip_url = f"{settings.API_V1_PREFIX}/jobs/{job.id}/download-zip" if job.zip_path and os.path.isfile(job.zip_path) else None

    response_data = job.to_dict()
    response_data["zip_download_url"] = zip_url
    response_data["certificates"] = cert_responses

    return response_data


@router.get(
    "/{job_id}/download-zip",
    summary="Download all generated certificates as a ZIP archive",
    description="Retrieves a consolidated ZIP archive containing all successfully generated PDF certificates for this job.",
)
def download_job_zip(
    job_id: str,
    db: Session = Depends(get_db),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate job with ID '{job_id}' not found.",
        )

    if job.status in (JobStatus.PENDING, JobStatus.PROCESSING):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is currently '{job.status.value}'. Please wait until processing completes before downloading the ZIP.",
        )

    if not job.zip_path or not os.path.isfile(job.zip_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No certificate archive available for this job (no certificates were generated successfully).",
        )

    clean_title = "".join(c for c in job.title if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
    zip_filename = f"{clean_title}_certificates.zip"

    return FileResponse(
        path=job.zip_path,
        media_type="application/zip",
        filename=zip_filename,
    )
