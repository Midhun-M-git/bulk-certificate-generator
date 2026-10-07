import csv
import io
import json
import logging
import uuid
from datetime import datetime
from typing import List, Tuple, Optional
from email_validator import validate_email, EmailNotValidError
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.job import Job, JobStatus
from app.models.certificate import Certificate, CertificateStatus
from app.schemas.job import JobCreateRequest
from app.schemas.recipient import RecipientInput
from app.services.certificate_generator import CertificateGenerator
from app.services.storage_service import storage_service
from app.config import settings

logger = logging.getLogger(__name__)


def generate_certificate_number() -> str:
    """Generates a human-readable unique certificate number."""
    now_str = datetime.utcnow().strftime("%Y%m%d")
    short_uuid = uuid.uuid4().hex[:6].upper()
    return f"CERT-{now_str}-{short_uuid}"


def validate_recipient_data(name: Optional[str], email: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    Validates recipient name and email.
    Returns (is_valid, error_reason).
    """
    if not name or not name.strip():
        return False, "Recipient name cannot be empty or whitespace only"

    if email is not None and email.strip():
        try:
            # Validate syntax without requiring live DNS lookups for test speed/reliability
            validate_email(email.strip(), check_deliverability=False)
        except EmailNotValidError as exc:
            return False, f"Invalid recipient email: {str(exc)}"

    return True, None


def parse_recipients_from_csv(csv_content: bytes) -> List[RecipientInput]:
    """
    Parses CSV content bytes into a list of RecipientInput objects.
    Supports utf-8 and utf-8-sig (Excel BOM), case-insensitive header matching
    for name and email, and maps remaining columns to metadata dict.
    """
    try:
        decoded_text = csv_content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError("Invalid file encoding. Please upload a UTF-8 encoded CSV file.")

    reader = csv.DictReader(io.StringIO(decoded_text))
    if not reader.fieldnames:
        raise ValueError("CSV file is empty or missing a header row.")

    # Locate name and email columns case-insensitively
    name_col = None
    email_col = None

    for col in reader.fieldnames:
        normalized = col.strip().lower()
        if normalized in ("name", "full_name", "recipient_name", "participant_name", "student_name") and not name_col:
            name_col = col
        elif normalized in ("email", "email_address", "recipient_email", "mail") and not email_col:
            email_col = col

    if not name_col:
        raise ValueError("CSV must contain a 'name' or 'full_name' column header.")

    recipients = []
    for row in reader:
        # Check if entire row is empty
        if not any(val and val.strip() for val in row.values() if val is not None):
            continue

        raw_name = (row.get(name_col) or "").strip()
        raw_email = (row.get(email_col) or "").strip() if email_col and row.get(email_col) else None

        # Collect metadata from remaining columns
        metadata = {}
        for k, v in row.items():
            if k not in (name_col, email_col) and v is not None and v.strip():
                metadata[k.strip()] = v.strip()

        recipients.append(
            RecipientInput(
                name=raw_name,
                email=raw_email,
                metadata=metadata if metadata else None
            )
        )

    if not recipients:
        raise ValueError("No recipient rows found in the CSV file.")

    return recipients


class JobService:

    @staticmethod
    def create_generation_job(db: Session, request: JobCreateRequest) -> Job:
        """
        Creates a new Job record and populates Certificate rows for all recipients.
        Recipient data is validated; any invalid recipient is recorded as FAILED upfront,
        preventing it from stopping valid recipients in the same bulk job.
        """
        job = Job(
            id=str(uuid.uuid4()),
            title=request.title.strip(),
            issuer_name=request.issuer_name.strip(),
            issue_date=request.issue_date.strip(),
            description=request.description.strip() if request.description else None,
            status=JobStatus.PENDING,
            total_count=len(request.recipients),
            processed_count=0,
            success_count=0,
            failed_count=0,
            created_at=datetime.utcnow()
        )
        db.add(job)

        # Create certificate records
        for item in request.recipients:
            is_valid, validation_error = validate_recipient_data(item.name, item.email)

            cert_num = generate_certificate_number()
            meta_str = json.dumps(item.metadata) if item.metadata else None

            if is_valid:
                cert = Certificate(
                    id=str(uuid.uuid4()),
                    job_id=job.id,
                    certificate_number=cert_num,
                    recipient_name=item.name.strip(),
                    recipient_email=item.email.strip() if item.email else None,
                    metadata_json=meta_str,
                    status=CertificateStatus.PENDING,
                    created_at=datetime.utcnow()
                )
            else:
                # Flag as failed immediately due to invalid data
                clean_name = item.name.strip() if (item.name and item.name.strip()) else "<Invalid Name>"
                cert = Certificate(
                    id=str(uuid.uuid4()),
                    job_id=job.id,
                    certificate_number=cert_num,
                    recipient_name=clean_name,
                    recipient_email=item.email.strip() if item.email else None,
                    metadata_json=meta_str,
                    status=CertificateStatus.FAILED,
                    failure_reason=validation_error,
                    created_at=datetime.utcnow()
                )
                job.failed_count += 1
                job.processed_count += 1

            db.add(cert)

        # If all recipients failed initial validation upfront
        if job.total_count > 0 and job.failed_count == job.total_count:
            job.status = JobStatus.FAILED
            job.completed_at = datetime.utcnow()
            job.error_message = "All recipient records failed validation."

        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def process_job(job_id: str):
        """
        Background worker task: Generates certificates for all pending recipients in the job.
        Runs in an independent database session for clean transaction boundaries.
        """
        db: Session = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                logger.error(f"Job with id {job_id} not found in background worker.")
                return

            # If already marked FAILED upfront
            if job.status == JobStatus.FAILED:
                return

            job.status = JobStatus.PROCESSING
            job.started_at = datetime.utcnow()
            db.commit()

            pending_certs = (
                db.query(Certificate)
                .filter(Certificate.job_id == job_id, Certificate.status == CertificateStatus.PENDING)
                .all()
            )

            for cert in pending_certs:
                cert_file_path = storage_service.get_certificate_path(job_id, cert.id)
                meta = json.loads(cert.metadata_json) if cert.metadata_json else None

                try:
                    # Render certificate PDF using the predefined template
                    file_size = CertificateGenerator.generate(
                        output_path=str(cert_file_path),
                        recipient_name=cert.recipient_name,
                        event_title=job.title,
                        issuer_name=job.issuer_name,
                        issue_date=job.issue_date,
                        certificate_number=cert.certificate_number,
                        description=job.description,
                        metadata=meta,
                    )

                    cert.status = CertificateStatus.SUCCESS
                    cert.file_path = str(cert_file_path)
                    cert.file_size_bytes = file_size
                    cert.generated_at = datetime.utcnow()
                    cert.failure_reason = None
                    job.success_count += 1

                except Exception as exc:
                    logger.exception(f"Failed generating certificate for {cert.recipient_name}: {exc}")
                    cert.status = CertificateStatus.FAILED
                    cert.failure_reason = f"Rendering error: {str(exc)}"
                    job.failed_count += 1

                finally:
                    job.processed_count += 1
                    # Save progress continuously so polling status reflects live updates
                    db.commit()

            # Refresh counts and determine final job status
            if job.success_count == job.total_count:
                job.status = JobStatus.COMPLETED
            elif job.success_count > 0:
                job.status = JobStatus.PARTIAL_SUCCESS
            else:
                job.status = JobStatus.FAILED

            job.completed_at = datetime.utcnow()

            # Create bulk ZIP archive if any certificates succeeded
            if job.success_count > 0:
                successful_certs = (
                    db.query(Certificate)
                    .filter(Certificate.job_id == job_id, Certificate.status == CertificateStatus.SUCCESS)
                    .all()
                )
                cert_dicts = [
                    {
                        "file_path": c.file_path,
                        "recipient_name": c.recipient_name,
                        "certificate_number": c.certificate_number,
                    }
                    for c in successful_certs
                ]
                zip_path = storage_service.create_job_zip(job_id, cert_dicts)
                job.zip_path = zip_path

            db.commit()
            logger.info(f"Job {job_id} finished processing with status {job.status.value}")

        except Exception as exc:
            logger.exception(f"Unexpected error processing job {job_id}: {exc}")
            try:
                job = db.query(Job).filter(Job.id == job_id).first()
                if job:
                    job.status = JobStatus.FAILED
                    job.error_message = f"Job processing crashed: {str(exc)}"
                    job.completed_at = datetime.utcnow()
                    db.commit()
            except Exception:
                pass
        finally:
            db.close()


job_service = JobService()
