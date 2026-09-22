"""
Test Suite for Human Edit Persistence & Compliance Governance.
Verifies the complete flow:
1. Edit content -> persists to SQLite under content_id.
2. Reload from database -> edited content returned.
3. Old compliance verdict invalidated -> re-evaluated on edited copy.
4. If edited content fails compliance -> remains pending and CANNOT be approved.
5. If edited content passes compliance -> can proceed to approval.
6. Original content and human edit note preserved in feedback audit trail & generation_metadata.
7. Editing an approved asset resets status to 'pending'.
8. API endpoint /content/{content_id}/edit executes full validation & persistence.
"""

import os
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from backend.database import init_db, get_connection
from backend import models
from backend.main import app
from backend.agents.compliance_agent import ComplianceAgent

TEST_DB_PATH = str(Path(__file__).resolve().parent / "test_human_edit.db")


@pytest.fixture(autouse=True)
def setup_teardown_test_db(monkeypatch):
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("JA_ASSURE_DB_PATH", TEST_DB_PATH)
    monkeypatch.setenv("JA_ASSURE_DEMO_DB_PATH", TEST_DB_PATH)
    init_db(TEST_DB_PATH)
    yield
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass


def test_edit_persists_to_database_and_reloads_updated_content():
    """Verify that editing content persists the new copy to SQLite under content_id and reloads cleanly."""
    original_text = "Protecting retail diamond inventories with specialized vault coverage."
    item = models.insert_content(
        brand="Jade",
        platform="LinkedIn",
        content_type="post",
        content=original_text,
        compliance_result={"status": "pass", "reasons": []},
        status="pending",
        db_path=TEST_DB_PATH,
    )
    content_id = item["id"]

    edited_text = "Refined retail jewellery coverage subject to vault underwriting and terms."
    updated = models.edit_content(
        content_id=content_id,
        edited_content=edited_text,
        tag="other",
        note="Refined disclaimer for vault protection",
        db_path=TEST_DB_PATH,
    )

    assert updated["id"] == content_id
    assert updated["content"] == edited_text
    assert updated["status"] == "pending"

    # Reload fresh from SQLite
    reloaded = models.get_content_by_id(content_id, db_path=TEST_DB_PATH)
    assert reloaded is not None
    assert reloaded["content"] == edited_text
    assert reloaded["id"] == content_id


def test_edit_invalidates_old_compliance_and_reevaluates():
    """Verify that when content changes, the old compliance result is invalidated and re-evaluated."""
    ca = ComplianceAgent()
    
    # Insert initially failing content with prohibited guaranteed payout
    flawed_text = "We promise a guaranteed payout for every jewellery loss under Jade."
    initial_comp = ca.check(flawed_text, "Jade")
    assert initial_comp["status"] == "fail"

    item = models.insert_content(
        brand="Jade",
        platform="LinkedIn",
        content_type="post",
        content=flawed_text,
        compliance_result=initial_comp,
        status="pending",
        db_path=TEST_DB_PATH,
    )
    content_id = item["id"]

    # Reviewer edits the copy to fix the flaw
    compliant_text = "Specialist Jewellers Block insurance tailored to secure premises and vault standards, subject to policy terms and conditions."
    updated = models.edit_content(
        content_id=content_id,
        edited_content=compliant_text,
        tag="inaccurate_claim",
        note="Removed guaranteed payout language",
        db_path=TEST_DB_PATH,
    )

    # Compliance must be re-evaluated and now PASS
    assert updated["compliance_result"]["status"] == "pass"
    assert updated["compliance_result"]["risk_score"] == 0.0
    assert updated["risk_level"] == "LOW"


def test_failed_edited_content_cannot_be_approved():
    """Governance Test: If an edit introduces a compliance violation, approval must be BLOCKED."""
    # Insert initially compliant content
    clean_text = "Comprehensive clinical risk advisory for medical practitioners."
    item = models.insert_content(
        brand="DoctorShield",
        platform="LinkedIn",
        content_type="post",
        content=clean_text,
        compliance_result={"status": "pass", "reasons": []},
        status="pending",
        db_path=TEST_DB_PATH,
    )
    content_id = item["id"]

    # Reviewer edits and inadvertently adds an absolute claim
    risky_edit = "DoctorShield promises guaranteed dismissal of every patient complaint."
    updated = models.edit_content(
        content_id=content_id,
        edited_content=risky_edit,
        db_path=TEST_DB_PATH,
    )

    assert updated["compliance_result"]["status"] == "fail"
    assert updated["status"] == "pending"

    # Attempt to approve must fail
    with pytest.raises(ValueError) as exc:
        models.approve_content(content_id, db_path=TEST_DB_PATH)
    assert "Compliance Governance Violation" in str(exc.value)


def test_passed_edited_content_can_proceed_to_approval():
    """Governance Test: When an edit makes content compliant, human approval can proceed."""
    flawed_text = "DoctorShield offers complete immunity from malpractice claims."
    item = models.insert_content(
        brand="DoctorShield",
        platform="LinkedIn",
        content_type="post",
        content=flawed_text,
        compliance_result={"status": "fail", "reasons": [{"rule": "NO_ABSOLUTE_PROTECTION"}]},
        status="pending",
        db_path=TEST_DB_PATH,
    )
    content_id = item["id"]

    # Fix via human edit
    remedied_text = "DoctorShield provides specialist medico-legal defense coverage subject to policy terms and conditions."
    updated = models.edit_content(
        content_id=content_id,
        edited_content=remedied_text,
        tag="inaccurate_claim",
        note="Replaced immunity with qualified indemnity coverage",
        db_path=TEST_DB_PATH,
    )

    assert updated["compliance_result"]["status"] == "pass"
    assert updated["status"] == "pending"

    # Human approval now succeeds
    approved = models.approve_content(content_id, db_path=TEST_DB_PATH)
    assert approved["status"] == "approved"


def test_original_content_and_audit_history_preserved():
    """Verify that original content is permanently preserved in feedback table and generation metadata."""
    original_text = "Original draft before human reviewer intervention."
    item = models.insert_content(
        brand="Jade",
        platform="LinkedIn",
        content_type="post",
        content=original_text,
        compliance_result={"status": "pass", "reasons": []},
        status="pending",
        db_path=TEST_DB_PATH,
    )
    content_id = item["id"]

    edited_text = "Updated draft refined by human reviewer for clarity."
    edit_note = "Polished wording for institutional luxury clients."
    updated = models.edit_content(
        content_id=content_id,
        edited_content=edited_text,
        tag="off_brand_tone",
        note=edit_note,
        db_path=TEST_DB_PATH,
    )

    # 1. Verify generation_metadata retains original content and history
    meta = updated.get("generation_metadata") or {}
    assert meta.get("human_edited") is True
    assert meta.get("original_content") == original_text
    assert len(meta.get("edit_history", [])) >= 1
    assert meta["edit_history"][0]["previous_content"] == original_text
    assert meta["edit_history"][0]["note"] == edit_note

    # 2. Verify feedback audit trail permanently stored
    fb_list = models.list_all_feedback(db_path=TEST_DB_PATH)
    assert len(fb_list) >= 1
    matched_fb = next((f for f in fb_list if f["content_id"] == content_id), None)
    assert matched_fb is not None
    assert matched_fb["original_content"] == original_text
    assert matched_fb["corrected_content"] == edited_text
    assert matched_fb["note"] == edit_note
    assert matched_fb["tag"] == "off_brand_tone"


def test_editing_approved_content_resets_status_to_pending():
    """State Machine Test: Editing an already approved asset must reset status to 'pending'."""
    item = models.insert_content(
        brand="Jade",
        platform="LinkedIn",
        content_type="post",
        content="Approved post text ready for publishing.",
        compliance_result={"status": "pass", "reasons": []},
        status="pending",
        db_path=TEST_DB_PATH,
    )
    models.approve_content(item["id"], db_path=TEST_DB_PATH)
    assert models.get_content_by_id(item["id"], db_path=TEST_DB_PATH)["status"] == "approved"

    # Now human edits the approved copy
    new_copy = "Revised post text requiring fresh compliance sign-off."
    edited = models.edit_content(
        content_id=item["id"],
        edited_content=new_copy,
        note="Post-approval copy modification",
        db_path=TEST_DB_PATH,
    )

    assert edited["status"] == "pending"
    assert edited["content"] == new_copy


def test_api_endpoint_edit_content_flow(monkeypatch):
    """Test the complete API flow: POST /content/{content_id}/edit -> schemas -> DB -> compliance -> response."""
    # Point models default db_path to TEST_DB_PATH for this test
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("JA_ASSURE_DB_PATH", TEST_DB_PATH)
    monkeypatch.setenv("JA_ASSURE_DEMO_DB_PATH", TEST_DB_PATH)

    item = models.insert_content(
        brand="DoctorShield",
        platform="LinkedIn",
        content_type="post",
        content="Clinical indemnity defense covering medical claims.",
        compliance_result={"status": "pass", "reasons": []},
        status="pending",
        db_path=TEST_DB_PATH,
    )
    content_id = item["id"]

    client = TestClient(app)
    response = client.post(
        f"/content/{content_id}/edit",
        json={
            "edited_content": "Healthcare liability defense strictly subject to policy terms and MAS guidelines.",
            "tag": "human_edit",
            "note": "Added MAS governance reference",
            "issue_type": "human_edit",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == content_id
    assert "MAS guidelines" in data["content"]
    assert data["status"] == "pending"
    assert data["compliance_result"]["status"] == "pass"

    # Verify database directly
    db_item = models.get_content_by_id(content_id, db_path=TEST_DB_PATH)
    assert "MAS guidelines" in db_item["content"]


def test_invalid_short_edit_rejected():
    """Verify that attempting to edit content to empty or fewer than 5 characters raises validation error."""
    item = models.insert_content(
        brand="Jade",
        platform="LinkedIn",
        content_type="post",
        content="Standard commercial jewellery insurance.",
        compliance_result={"status": "pass", "reasons": []},
        status="pending",
        db_path=TEST_DB_PATH,
    )

    with pytest.raises(ValueError) as exc1:
        models.edit_content(item["id"], "", db_path=TEST_DB_PATH)
    assert "cannot be empty" in str(exc1.value)

    with pytest.raises(ValueError) as exc2:
        models.edit_content(item["id"], "Tiny", db_path=TEST_DB_PATH)
    assert "at least 5 characters" in str(exc2.value)
