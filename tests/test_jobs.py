from pathlib import Path


def test_create_job_and_generate_certificates(client):
    response = client.post("/api/jobs", json={
        "event_name": "AEREO Engineering Workshop",
        "certificate_title": "Certificate of Participation",
        "recipients": [
            {"name": "Alice", "email": "alice@example.com"},
            {"name": "Bob", "email": "bob@example.com"},
        ],
    })
    assert response.status_code == 202
    body = response.json()
    assert body["total_recipients"] == 2

    job = client.get(f"/api/jobs/{body['id']}").json()
    assert job["status"] == "COMPLETED"
    assert job["successful_count"] == 2
    assert job["failed_count"] == 0
    assert job["progress_percent"] == 100.0

    for recipient in job["recipients"]:
        cert = client.get(recipient["certificate_url"])
        assert cert.status_code == 200
        assert cert.headers["content-type"] == "application/pdf"


def test_input_validation(client):
    response = client.post("/api/jobs", json={
        "event_name": "Workshop",
        "recipients": [{"name": "   "}],
    })
    assert response.status_code == 422


def test_duplicate_recipient_rejected(client):
    response = client.post("/api/jobs", json={
        "event_name": "Workshop",
        "recipients": [
            {"name": "Alice"},
            {"name": "Alice"},
        ],
    })
    assert response.status_code == 422


def test_individual_certificate_failure_does_not_stop_batch(client, monkeypatch):
    from app.services import job_processor

    real_generate = job_processor.generate_certificate

    def flaky_generate(**kwargs):
        if kwargs["recipient_name"] == "Broken User":
            raise RuntimeError("Simulated certificate generation failure")
        return real_generate(**kwargs)

    monkeypatch.setattr(job_processor, "generate_certificate", flaky_generate)

    response = client.post("/api/jobs", json={
        "event_name": "Failure Isolation Test",
        "recipients": [
            {"name": "Working User"},
            {"name": "Broken User"},
            {"name": "Another Working User"},
        ],
    })
    assert response.status_code == 202
    job = client.get(f"/api/jobs/{response.json()['id']}").json()

    assert job["status"] == "COMPLETED_WITH_ERRORS"
    assert job["successful_count"] == 2
    assert job["failed_count"] == 1
    failed = next(r for r in job["recipients"] if r["name"] == "Broken User")
    assert failed["status"] == "FAILED"
    assert "Simulated certificate generation failure" in failed["error_message"]


def test_unknown_job_returns_404(client):
    response = client.get("/api/jobs/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_unknown_certificate_returns_404(client):
    response = client.get(
        "/api/certificates/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


def test_blank_event_name_is_rejected(client):
    response = client.post(
        "/api/jobs",
        json={
            "event_name": "   ",
            "recipients": [{"name": "Alice"}],
        },
    )
    assert response.status_code == 422