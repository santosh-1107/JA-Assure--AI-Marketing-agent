"""
Unit and integration tests for SQLite database operations and governance rules.
"""

import os
import pytest
from pathlib import Path
from backend.database import init_db, get_connection
from backend import models

TEST_DB_PATH = str(Path(__file__).resolve().parent / "test_ja_assure.db")


@pytest.fixture(autouse=True)
def setup_teardown_db():
    """Create fresh isolated test database for each test and cleanup afterwards."""
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    init_db(TEST_DB_PATH)
    yield
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


def test_content_insertion_and_retrieval():
    """Verify content insertion defaults to status='pending'."""
    item = models.insert_content(
        brand="Jade",
        platform="LinkedIn",
        content_type="post",
        content="Bespoke luxury jewelry coverage.",
        db_path=TEST_DB_PATH,
    )
    assert item["id"] is not None
    assert item["brand"] == "Jade"
    assert item["status"] == "pending"

    fetched = models.get_content_by_id(item["id"], db_path=TEST_DB_PATH)
    assert fetched is not None
    assert fetched["content"] == "Bespoke luxury jewelry coverage."


def test_human_approval_workflow():
    """Verify human reviewer can approve pending content."""
    item = models.insert_content(
        brand="DoctorShield",
        platform="LinkedIn",
        content_type="post",
        content="Clinical indemnity post.",
        compliance_result={"status": "pass", "reasons": []},
        status="pending",
        db_path=TEST_DB_PATH,
    )

    approved = models.approve_content(item["id"], db_path=TEST_DB_PATH)
    assert approved["status"] == "approved"

    # Verify cannot re-approve already approved content inappropriately
    with pytest.raises(ValueError):
        models.approve_content(item["id"], db_path=TEST_DB_PATH)


def test_reject_workflow_and_feedback_storage():
    """Verify reject requires tag and note, updates status, and writes to feedback table."""
    item = models.insert_content(
        brand="Jade",
        platform="LinkedIn",
        content_type="post",
        content="Guaranteed instant cash payouts!",
        status="pending",
        db_path=TEST_DB_PATH,
    )

    # Rejection without note must fail
    with pytest.raises(ValueError):
        models.reject_content(item["id"], tag="inaccurate_claim", note="", db_path=TEST_DB_PATH)

    # Rejection with invalid tag must fail
    with pytest.raises(ValueError):
        models.reject_content(item["id"], tag="invalid_random_tag", note="Some note", db_path=TEST_DB_PATH)

    # Valid rejection
    rejected = models.reject_content(
        item["id"],
        tag="inaccurate_claim",
        note="Avoid guaranteed payout claims under MAS guidelines.",
        db_path=TEST_DB_PATH,
    )
    assert rejected["status"] == "rejected"

    # Verify feedback was stored
    feedback_list = models.get_recent_feedback("Jade", n=5, db_path=TEST_DB_PATH)
    assert len(feedback_list) == 1
    assert feedback_list[0]["tag"] == "inaccurate_claim"
    assert "Avoid guaranteed payout" in feedback_list[0]["note"]


def test_schedule_rule_enforces_previous_human_approval():
    """
    CRITICAL SECURITY CHECK:
    Verify content CANNOT reach 'scheduled' status unless it is ALREADY 'approved'.
    Direct Content Agent -> Scheduled is strictly prevented.
    """
    pending_item = models.insert_content(
        brand="DoctorShield",
        platform="LinkedIn",
        content_type="post",
        content="Unreviewed draft post.",
        compliance_result={"status": "pass", "reasons": []},
        status="pending",
        db_path=TEST_DB_PATH,
    )

    # Attempting to schedule pending content must raise ValueError
    with pytest.raises(ValueError) as exc_info:
        models.schedule_content(pending_item["id"], db_path=TEST_DB_PATH)
    assert "Security Rule Violation" in str(exc_info.value)

    # Now simulate human approval
    models.approve_content(pending_item["id"], db_path=TEST_DB_PATH)

    # Now scheduling must succeed
    scheduled = models.schedule_content(pending_item["id"], db_path=TEST_DB_PATH)
    assert scheduled["status"] == "scheduled"


def test_rejection_rate_calculation():
    """Verify rejection rate computation per cycle."""
    # Seed Cycle 1: 4 rejected, 1 approved -> 80%
    for i in range(4):
        c = models.insert_content(brand="Jade", platform="X", content_type="tweet", content=f"Bad {i}", cycle=1, status="pending", db_path=TEST_DB_PATH)
        models.reject_content(c["id"], tag="too_salesy", note="Too aggressive", db_path=TEST_DB_PATH)
    
    c_app = models.insert_content(brand="Jade", platform="X", content_type="tweet", content="Good", compliance_result={"status": "pass", "reasons": []}, cycle=1, status="pending", db_path=TEST_DB_PATH)
    models.approve_content(c_app["id"], db_path=TEST_DB_PATH)

    # Seed Cycle 2: 1 rejected, 4 approved -> 20%
    c2_bad = models.insert_content(brand="Jade", platform="X", content_type="tweet", content="Bad C2", cycle=2, status="pending", db_path=TEST_DB_PATH)
    models.reject_content(c2_bad["id"], tag="wrong_cta", note="Fix CTA", db_path=TEST_DB_PATH)
    for j in range(4):
        c2_ok = models.insert_content(brand="Jade", platform="X", content_type="tweet", content=f"Good {j}", compliance_result={"status": "pass", "reasons": []}, cycle=2, status="pending", db_path=TEST_DB_PATH)
        models.approve_content(c2_ok["id"], db_path=TEST_DB_PATH)

    stats = models.get_rejection_rate_by_cycle(db_path=TEST_DB_PATH)
    assert len(stats) == 2
    assert stats[0]["cycle"] == 1
    assert stats[0]["rejection_rate"] == 80.0
    assert stats[1]["cycle"] == 2
    assert stats[1]["rejection_rate"] == 20.0


def test_empty_database_safety():
    """Verify that an empty database does not crash any queries or analytics."""
    from backend.agents.feedback_agent import FeedbackAgent
    empty_fa = FeedbackAgent(db_path=TEST_DB_PATH)

    assert models.list_pending_content(db_path=TEST_DB_PATH) == []
    assert models.list_approved_content(db_path=TEST_DB_PATH) == []
    assert models.list_all_content(db_path=TEST_DB_PATH) == []
    assert models.list_all_feedback(db_path=TEST_DB_PATH) == []
    assert models.get_before_after_pairs(db_path=TEST_DB_PATH) == []
    assert models.list_leads(db_path=TEST_DB_PATH) == []

    analytics = empty_fa.get_rejection_rate_analytics()
    assert analytics["cycles"] == []
    assert analytics["total_reviewed"] == 0
    assert analytics["overall_rejection_rate"] == 0.0
