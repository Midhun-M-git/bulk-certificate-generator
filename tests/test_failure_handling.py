from unittest.mock import patch
from app.services.certificate_generator import CertificateGenerator


def test_mixed_batch_with_invalid_recipient_data(client):
    """
    Submitting a batch with invalid recipients must NOT abort the generation of valid ones.
    The job should reach PARTIAL_SUCCESS, with granular failure reasons for invalid items.
    """
    payload = {
        "title": "Cloud Architecture Summit",
        "issuer_name": "DevCorp",
        "issue_date": "October 7, 2026",
        "recipients": [
            {"name": "Valid Recipient 1", "email": "valid1@example.com"},
            {"name": "   ", "email": "blank_name@example.com"},  # Invalid name
            {"name": "Valid Recipient 2", "email": "valid2@example.com"},
            {"name": "Invalid Email Person", "email": "not-an-email"},  # Invalid email
        ],
    }

    create_res = client.post("/api/v1/jobs", json=payload)
    assert create_res.status_code == 202
    job_id = create_res.json()["job_id"]

    status_res = client.get(f"/api/v1/jobs/{job_id}")
    assert status_res.status_code == 200
    job_data = status_res.json()

    assert job_data["total_count"] == 4
    assert job_data["processed_count"] == 4
    assert job_data["success_count"] == 2
    assert job_data["failed_count"] == 2
    assert job_data["status"] == "PARTIAL_SUCCESS"

    certs = job_data["certificates"]
    assert len(certs) == 4

    # Verify individual statuses
    cert_map = {c["recipient_name"]: c for c in certs}

    assert cert_map["Valid Recipient 1"]["status"] == "SUCCESS"
    assert cert_map["Valid Recipient 1"]["download_url"] is not None

    assert cert_map["Valid Recipient 2"]["status"] == "SUCCESS"
    assert cert_map["Valid Recipient 2"]["download_url"] is not None

    assert cert_map["<Invalid Name>"]["status"] == "FAILED"
    assert "name cannot be empty" in cert_map["<Invalid Name>"]["failure_reason"].lower()

    assert cert_map["Invalid Email Person"]["status"] == "FAILED"
    assert "invalid recipient email" in cert_map["Invalid Email Person"]["failure_reason"].lower()


def test_runtime_generation_failure_isolation(client, monkeypatch):
    """
    If rendering a certificate raises an unhandled exception for one recipient,
    it must be isolated so that the rest of the batch completes successfully.
    """
    original_generate = CertificateGenerator.generate

    def mock_generate(output_path, recipient_name, *args, **kwargs):
        if "Flaky" in recipient_name:
            raise RuntimeError("Simulated rendering memory fault")
        return original_generate(output_path, recipient_name, *args, **kwargs)

    monkeypatch.setattr(CertificateGenerator, "generate", mock_generate)

    payload = {
        "title": "Robustness Testing Workshop",
        "issuer_name": "Quality Assurance Lab",
        "issue_date": "October 7, 2026",
        "recipients": [
            {"name": "Stable Recipient Alpha", "email": "alpha@example.com"},
            {"name": "Flaky Recipient Beta", "email": "beta@example.com"},
            {"name": "Stable Recipient Gamma", "email": "gamma@example.com"},
        ],
    }

    create_res = client.post("/api/v1/jobs", json=payload)
    job_id = create_res.json()["job_id"]

    status_res = client.get(f"/api/v1/jobs/{job_id}")
    job_data = status_res.json()

    assert job_data["status"] == "PARTIAL_SUCCESS"
    assert job_data["success_count"] == 2
    assert job_data["failed_count"] == 1

    cert_map = {c["recipient_name"]: c for c in job_data["certificates"]}
    assert cert_map["Stable Recipient Alpha"]["status"] == "SUCCESS"
    assert cert_map["Stable Recipient Gamma"]["status"] == "SUCCESS"
    assert cert_map["Flaky Recipient Beta"]["status"] == "FAILED"
    assert "simulated rendering memory fault" in cert_map["Flaky Recipient Beta"]["failure_reason"].lower()
