def test_create_generation_job_success(client):
    """Test successful submission of a bulk certificate generation job."""
    payload = {
        "title": "Machine Learning Fundamentals",
        "issuer_name": "AI Institute",
        "issue_date": "October 7, 2026",
        "description": "for successfully completing the core curriculum",
        "recipients": [
            {"name": "Alice Walker", "email": "alice@example.com"},
            {"name": "Bob Martin", "email": "bob@example.com"},
        ],
    }

    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 202

    data = response.json()
    assert "job_id" in data
    assert data["total_recipients"] == 2
    assert data["status"] in ("PENDING", "PROCESSING", "COMPLETED")
    assert f"/api/v1/jobs/{data['job_id']}" in data["status_url"]


def test_create_generation_job_missing_fields(client):
    """Test validation rejection when required top-level fields are missing."""
    # Missing title and issuer_name
    payload = {
        "issue_date": "October 7, 2026",
        "recipients": [{"name": "Alice", "email": "alice@example.com"}],
    }

    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422
