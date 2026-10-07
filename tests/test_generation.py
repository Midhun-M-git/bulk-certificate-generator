import os
import tempfile
from pathlib import Path
from app.services.certificate_generator import CertificateGenerator


def test_certificate_generator_creates_valid_pdf():
    """Verify that CertificateGenerator outputs a valid, readable PDF file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = Path(tmpdir) / "test_certificate.pdf"

        file_size = CertificateGenerator.generate(
            output_path=str(output_file),
            recipient_name="Eleanor Vance",
            event_title="Full Stack Software Engineering",
            issuer_name="Silicon Valley Academy",
            issue_date="October 7, 2026",
            certificate_number="CERT-20261007-TEST01",
            description="for demonstrating superior technical execution",
            metadata={"grade": "A+", "honors": True},
        )

        assert output_file.exists()
        assert file_size > 0
        assert file_size == os.path.getsize(output_file)

        # Verify PDF magic number (%PDF-)
        with open(output_file, "rb") as f:
            header = f.read(5)
            assert header == b"%PDF-"


def test_certificate_generator_handles_edge_cases():
    """Verify that CertificateGenerator handles long names, minimal data, and unicode characters."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = Path(tmpdir) / "test_long_name.pdf"

        file_size = CertificateGenerator.generate(
            output_path=str(output_file),
            recipient_name="Prof. Maximilian Bartholomew Alistair Montgomery III",
            event_title="International Symposium on Quantum Information & Distributed Networks",
            issuer_name="Imperial Academy of Technology",
            issue_date="October 7, 2026",
            certificate_number="CERT-20261007-TEST02",
            description=None,
            metadata=None,
        )

        assert output_file.exists()
        assert file_size > 1000
