import io
from app.services.job_service import parse_recipients_from_csv


def test_parse_recipients_from_csv_unit():
    """Unit test for CSV parsing with headers, BOM, and extra metadata columns."""
    csv_data = b"name,email,grade,department\nAlice Smith,alice@example.com,A+,Engineering\nBob Jones,bob@example.com,B,Product\n"
    recipients = parse_recipients_from_csv(csv_data)

    assert len(recipients) == 2
    assert recipients[0].name == "Alice Smith"
    assert recipients[0].email == "alice@example.com"
    assert recipients[0].metadata == {"grade": "A+", "department": "Engineering"}

    assert recipients[1].name == "Bob Jones"
    assert recipients[1].email == "bob@example.com"
    assert recipients[1].metadata == {"grade": "B", "department": "Product"}


def test_parse_recipients_from_csv_alternate_headers():
    """Unit test verifying case-insensitive header matching (e.g. Full_Name, Recipient_Email)."""
    csv_data = b"Full_Name,Recipient_Email,Cohort\nCharlie Brown,charlie@test.org,2026-Q1\n"
    recipients = parse_recipients_from_csv(csv_data)

    assert len(recipients) == 1
    assert recipients[0].name == "Charlie Brown"
    assert recipients[0].email == "charlie@test.org"
    assert recipients[0].metadata == {"Cohort": "2026-Q1"}


def test_csv_upload_endpoint_success(client):
    """Test POST /api/v1/jobs/upload-csv endpoint with multipart form data."""
    csv_content = "name,email,track\nJane Doe,jane@domain.com,Cloud\nJohn Doe,john@domain.com,Security\n"
    files = {
        "file": ("participants.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")
    }
    data = {
        "title": "Cloud and Security Workshop",
        "issuer_name": "Tech Corp",
        "issue_date": "October 7, 2026",
        "description": "for completing the combined track",
    }

    response = client.post("/api/v1/jobs/upload-csv", data=data, files=files)
    assert response.status_code == 202

    res_data = response.json()
    assert res_data["total_recipients"] == 2
    job_id = res_data["job_id"]

    # Poll status
    job_status = client.get(f"/api/v1/jobs/{job_id}").json()
    assert job_status["status"] == "COMPLETED"
    assert job_status["success_count"] == 2
    assert len(job_status["certificates"]) == 2


def test_csv_upload_missing_name_column(client):
    """Uploading a CSV without a name column header must return HTTP 400."""
    csv_content = "username,email\njane,jane@domain.com\n"
    files = {
        "file": ("invalid_headers.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")
    }
    data = {
        "title": "Test Title",
        "issuer_name": "Test Issuer",
        "issue_date": "October 7, 2026",
    }

    response = client.post("/api/v1/jobs/upload-csv", data=data, files=files)
    assert response.status_code == 400
    assert "must contain a 'name'" in response.json()["detail"].lower()


def test_csv_upload_non_csv_rejected(client):
    """Uploading a non-CSV file must return HTTP 400."""
    files = {
        "file": ("data.txt", io.BytesIO(b"Hello World"), "text/plain")
    }
    data = {
        "title": "Test Title",
        "issuer_name": "Test Issuer",
        "issue_date": "October 7, 2026",
    }

    response = client.post("/api/v1/jobs/upload-csv", data=data, files=files)
    assert response.status_code == 400
    assert "must be a .csv file" in response.json()["detail"].lower()
