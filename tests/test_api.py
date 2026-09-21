"""
FastAPI integration tests using TestClient.
"""

import os
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from backend.main import app
from backend.database import init_db
import backend.models as models

TEST_DB_PATH = str(Path(__file__).resolve().parent / "test_api.db")


@pytest.fixture(autouse=True)
def setup_teardown_api_db(monkeypatch):
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    monkeypatch.setenv("JA_ASSURE_DB_PATH", TEST_DB_PATH)
    init_db(TEST_DB_PATH)
    yield
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "llm" in data


def test_generate_content_api(client):
    payload = {
        "brand": "Jade",
        "platform": "LinkedIn",
        "content_type": "post",
        "topic": "Heirloom jewelry safeguarding",
        "cycle": 1,
        "force_trigger_flaw": False,
    }
    res = client.post("/content/generate", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["id"] is not None
    assert data["brand"] == "Jade"
    assert data["status"] == "pending"
    assert data["compliance_result"] is not None


def test_human_approve_and_reject_api(client):
    # 1. Generate an item
    gen_res = client.post(
        "/content/generate",
        json={
            "brand": "DoctorShield",
            "platform": "LinkedIn",
            "content_type": "post",
            "topic": "Clinical malpractice risk",
            "cycle": 1,
            "force_trigger_flaw": True,
        },
    )
    item_id = gen_res.json()["id"]

    # 2. Reject with feedback
    rej_res = client.post(
        f"/content/{item_id}/reject",
        json={
            "tag": "inaccurate_claim",
            "note": "Never guarantee legal case dismissal.",
        },
    )
    assert rej_res.status_code == 200
    assert rej_res.json()["status"] == "rejected"

    # 3. Regenerate
    regen_res = client.post(f"/content/{item_id}/regenerate")
    assert regen_res.status_code == 201
    regen_item = regen_res.json()
    assert regen_item["parent_id"] == item_id
    assert regen_item["compliance_result"]["status"] == "pass"

    # 4. Approve the regenerated variant
    app_res = client.post(f"/content/{regen_item['id']}/approve")
    assert app_res.status_code == 200
    assert app_res.json()["status"] == "approved"

    # 5. Schedule the approved variant
    sched_res = client.post(f"/content/{regen_item['id']}/schedule")
    assert sched_res.status_code == 200
    assert sched_res.json()["status"] == "scheduled"


def test_rejection_rate_endpoint(client):
    res = client.get("/analytics/rejection-rate")
    assert res.status_code == 200
    data = res.json()
    assert "cycles" in data
    assert "total_reviewed" in data
    assert "overall_rejection_rate" in data


def test_leads_endpoints(client):
    # Add a lead
    add_res = client.post(
        "/leads",
        json={
            "name": "Dr. Sarah Chen",
            "contact": "sarah.chen@clinic.sg",
            "vertical": "Clinics",
            "fit_score": 90,
            "outreach_draft": "Hello Dr. Chen, review your indemnity coverage.",
        },
    )
    assert add_res.status_code == 201
    lead_id = add_res.json()["id"]

    # List leads
    list_res = client.get("/leads")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    # Mark contacted
    contact_res = client.post(f"/leads/{lead_id}/contact")
    assert contact_res.status_code == 200
    assert contact_res.json()["status"] == "contacted"
