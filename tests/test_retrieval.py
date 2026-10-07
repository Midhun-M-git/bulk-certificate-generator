import io
import zipfile


def test_retrieve_individual_certificate_pdf(client):
    """Test downloading and previewing an individual generated PDF certificate."""
    payload = {
        "title": "Data Science Bootcamp",
        "issuer_name": "Analytics Academy",
        "issue_date": "October 7, 2026",
        "recipients": [{"name": "Lucas Scott", "email": "lucas@example.com"}],
    }

    create_res = client.post("/api/v1/jobs", json=payload)
    job_id = create_res.json()["job_id"]

    job_res = client.get(f"/api/v1/jobs/{job_id}")
    cert_id = job_res.json()["certificates"][0]["id"]

    # 1. Get metadata
    meta_res = client.get(f"/api/v1/certificates/{cert_id}")
    assert meta_res.status_code == 200
    assert meta_res.json()["recipient_name"] == "Lucas Scott"
    assert meta_res.json()["status"] == "SUCCESS"

    # 2. Download PDF
    dl_res = client.get(f"/api/v1/certificates/{cert_id}/download")
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"] == "application/pdf"
    assert "attachment" in dl_res.headers["content-disposition"]
    assert dl_res.content.startswith(b"%PDF-")

    # 3. Preview PDF
    prev_res = client.get(f"/api/v1/certificates/{cert_id}/preview")
    assert prev_res.status_code == 200
    assert prev_res.headers["content-type"] == "application/pdf"
    assert prev_res.headers["content-disposition"] == "inline"
    assert prev_res.content.startswith(b"%PDF-")


def test_retrieve_job_zip_archive(client):
    """Test downloading the consolidated ZIP archive of all generated certificates."""
    payload = {
        "title": "Cybersecurity Intensive",
        "issuer_name": "Security Labs",
        "issue_date": "October 7, 2026",
        "recipients": [
            {"name": "Alice Security", "email": "alice@sec.org"},
            {"name": "Bob Defense", "email": "bob@sec.org"},
        ],
    }

    create_res = client.post("/api/v1/jobs", json=payload)
    job_id = create_res.json()["job_id"]

    zip_res = client.get(f"/api/v1/jobs/{job_id}/download-zip")
    assert zip_res.status_code == 200
    assert zip_res.headers["content-type"] == "application/zip"

    # Verify zip content structure
    zip_bytes = io.BytesIO(zip_res.content)
    with zipfile.ZipFile(zip_bytes, "r") as zf:
        namelist = zf.namelist()
        assert len(namelist) == 2
        for name in namelist:
            assert name.endswith(".pdf")
            data = zf.read(name)
            assert data.startswith(b"%PDF-")


def test_retrieval_error_cases(client):
    """Test retrieval edge cases for non-existent and failed certificates."""
    # 404 on nonexistent cert
    res = client.get("/api/v1/certificates/non-existent-uuid/download")
    assert res.status_code == 404

    # 404 on nonexistent job zip
    res = client.get("/api/v1/jobs/non-existent-job/download-zip")
    assert res.status_code == 404
