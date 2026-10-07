import os
import zipfile
from pathlib import Path
from typing import List, Optional
from app.config import settings


class StorageService:
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or settings.STORAGE_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_job_dir(self, job_id: str) -> Path:
        """Returns the directory dedicated to a job, ensuring it exists."""
        job_dir = self.base_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        return job_dir

    def get_certificate_path(self, job_id: str, certificate_id: str) -> Path:
        """Returns the absolute file path for an individual certificate PDF."""
        job_dir = self.get_job_dir(job_id)
        return job_dir / f"{certificate_id}.pdf"

    def get_zip_path(self, job_id: str) -> Path:
        """Returns the file path for the job's consolidated ZIP archive."""
        job_dir = self.get_job_dir(job_id)
        return job_dir / f"certificates_job_{job_id[:8]}.zip"

    def create_job_zip(self, job_id: str, certificate_records: List[dict]) -> Optional[str]:
        """
        Creates a ZIP archive containing all successfully generated certificates.
        Names individual files inside the zip cleanly: e.g. 'John_Doe_CERT-123.pdf'.
        """
        valid_files = []
        for cert in certificate_records:
            file_path = cert.get("file_path")
            if file_path and os.path.isfile(file_path):
                # Clean filename inside zip
                safe_name = "".join(c for c in cert.get("recipient_name", "recipient") if c.isalnum() or c in (" ", "_", "-")).strip()
                safe_name = safe_name.replace(" ", "_")
                cert_num = cert.get("certificate_number", cert.get("id", "cert"))
                archive_name = f"{safe_name}_{cert_num}.pdf"
                valid_files.append((file_path, archive_name))

        if not valid_files:
            return None

        zip_dest = self.get_zip_path(job_id)
        with zipfile.ZipFile(zip_dest, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path, arcname in valid_files:
                zipf.write(file_path, arcname=arcname)

        return str(zip_dest)


storage_service = StorageService()
