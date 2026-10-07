def test_job_status_and_progress_lifecycle(client):
    """Test job progress tracking and status retrieval through the full lifecycle."""
    payload = {
        "title": "Backend Engineering Certification",
        "issuer_name": "Tech Corp",
        "issue_date": "October 7, 2026",
        "description": "Excellence in APIs and Databases",
        "recipients": [
            {"name": "Dev One", "email": "dev1@example.com"},
            {"name": "Dev Two", "email": "dev2@example.com"},
            {"name": "Dev Three", "email": "dev3@example.com"},
        ],
    }

    # 1. Create Job
    create_res = client.post("/api/v1/jobs", json=payload)
    assert create_res.status_code == 202
    job_id = create_res.json()["job_id"]

    # 2. Check Job Status
    status_res = client.get(f"/api/v1/jobs/{job_id}")
    assert status_res.status_code == 200

    job_data = status_res.json()
    assert job_data["id"] == job_id
    assert job_data["title"] == payload["title"]
    assert job_data["total_count"] == 3
    assert job_data["processed_count"] == 3
    assert job_data["success_count"] == 3
    assert job_data["failed_count"] == 0
    assert job_data["status"] == "COMPLETED"
    assert job_data["progress_percentage"] == 100.0
    assert job_data["has_zip"] is True
    assert job_data["zip_download_url"] is not None

    # Check recipient certificates list
    assert len(job_data["certificates"]) == 3
    for cert in job_data["certificates"]:
        assert cert["status"] == "SUCCESS"
        assert cert["download_url"] is not None
        assert cert["preview_url"] is not None
        assert cert["certificate_number"].startswith("CERT-")
        assert cert["file_size_bytes"] > 0


def test_list_jobs_endpoint(client):
    """Test listing jobs returns summary records."""
    res = client.get("/api/v1/jobs")
    assert res.status_code == 200
    jobs = res.json()
    assert isinstance(jobs, list)
    assert len(jobs) >= 1
