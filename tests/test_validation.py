from app.services.job_service import validate_recipient_data


def test_validation_empty_recipient_list(client):
    """Submitting a request with an empty recipients list must fail validation (HTTP 422)."""
    payload = {
        "title": "Cloud Computing 101",
        "issuer_name": "DevAcademy",
        "issue_date": "October 7, 2026",
        "recipients": [],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422


def test_validation_empty_title_or_issuer(client):
    """Submitting empty string for title or issuer must fail validation (HTTP 422)."""
    payload = {
        "title": "",
        "issuer_name": "TechNova",
        "issue_date": "October 7, 2026",
        "recipients": [{"name": "John Doe", "email": "john@example.com"}],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422


def test_recipient_data_validator_logic():
    """Unit test for validate_recipient_data helper."""
    # Valid cases
    valid, err = validate_recipient_data("Alice Smith", "alice@example.com")
    assert valid is True
    assert err is None

    valid, err = validate_recipient_data("Bob Jones", None)
    assert valid is True
    assert err is None

    # Invalid names
    valid, err = validate_recipient_data("", "alice@example.com")
    assert valid is False
    assert "name cannot be empty" in err.lower()

    valid, err = validate_recipient_data("   ", "alice@example.com")
    assert valid is False
    assert "name cannot be empty" in err.lower()

    # Invalid emails
    valid, err = validate_recipient_data("Charlie", "not-a-valid-email")
    assert valid is False
    assert "invalid recipient email" in err.lower()


def test_batch_size_limit_rejection(client, monkeypatch):
    """Requests exceeding maximum batch limit must be rejected with HTTP 400."""
    from app.config import settings
    monkeypatch.setattr(settings, "MAX_RECIPIENTS_PER_BATCH", 3)

    payload = {
        "title": "Large Batch Test",
        "issuer_name": "Institute",
        "issue_date": "October 7, 2026",
        "recipients": [
            {"name": f"User {i}", "email": f"user{i}@example.com"}
            for i in range(5)
        ],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 400
    assert "exceeds maximum allowed" in response.json()["detail"].lower()
