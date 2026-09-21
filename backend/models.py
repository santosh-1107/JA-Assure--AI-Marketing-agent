"""
Data models and CRUD operations for JA Assure AI Marketing Agent.
Strictly enforces compliance state machines and human review governance.
"""

import json
import sqlite3
from typing import Any, Dict, List, Optional, Tuple
from backend.database import get_connection

VALID_FEEDBACK_TAGS = {
    "too_salesy",
    "inaccurate_claim",
    "off_brand_tone",
    "wrong_cta",
    "other",
}

VALID_STATUSES = {"pending", "approved", "rejected", "scheduled"}
VALID_BRANDS = {"Jade", "DoctorShield"}
VALID_PLATFORMS = {"LinkedIn", "Instagram", "X"}
VALID_CONTENT_TYPES = {"post", "carousel", "tweet", "video_script"}


# =====================================================================
# Content Queue Operations
# =====================================================================

def insert_content(
    brand: str,
    platform: str,
    content_type: str,
    content: str,
    compliance_result: Optional[Dict[str, Any]] = None,
    cycle: int = 1,
    parent_id: Optional[int] = None,
    fixed_issue: Optional[str] = None,
    sources: Optional[List[Dict[str, Any]]] = None,
    status: str = "pending",
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Insert a newly generated marketing asset into the content_queue.
    Defaults to status='pending' requiring human review.
    Attaches verified JA Assure knowledge sources.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    comp_str = json.dumps(compliance_result) if compliance_result else None
    sources_str = json.dumps(sources) if sources else None

    cursor.execute(
        """
        INSERT INTO content_queue (brand, platform, content_type, content, status, compliance_result, cycle, parent_id, fixed_issue, sources)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (brand, platform, content_type, content, status, comp_str, cycle, parent_id, fixed_issue, sources_str),
    )
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return get_content_by_id(new_id, db_path=db_path)  # type: ignore


def get_content_by_id(content_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Fetch a single content queue item by ID."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM content_queue WHERE id = ?", (content_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    item = dict(row)
    for field in ["compliance_result", "sources"]:
        if item.get(field):
            try:
                item[field] = json.loads(item[field])
            except Exception:
                pass
    return item


def list_pending_content(brand: Optional[str] = None, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List content items awaiting human review.
    Sorts non-compliant (FAIL) items first for immediate visibility, then by created_at DESC.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    query = """
        SELECT * FROM content_queue
        WHERE status = 'pending'
    """
    params: List[Any] = []
    if brand:
        query += " AND brand = ?"
        params.append(brand)

    # Sort so items containing '"status": "fail"' in compliance_result come first
    query += """
        ORDER BY 
            CASE 
                WHEN compliance_result LIKE '%"status": "fail"%' THEN 0 
                ELSE 1 
            END ASC,
            created_at DESC
    """

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    results = []
    for row in rows:
        item = dict(row)
        for field in ["compliance_result", "sources"]:
            if item.get(field):
                try:
                    item[field] = json.loads(item[field])
                except Exception:
                    pass
        results.append(item)
    return results


def list_approved_content(brand: Optional[str] = None, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """List approved marketing assets ready for publishing / scheduling."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    query = "SELECT * FROM content_queue WHERE status IN ('approved', 'scheduled')"
    params: List[Any] = []
    if brand:
        query += " AND brand = ?"
        params.append(brand)
    query += " ORDER BY created_at DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    results = []
    for row in rows:
        item = dict(row)
        for field in ["compliance_result", "sources"]:
            if item.get(field):
                try:
                    item[field] = json.loads(item[field])
                except Exception:
                    pass
        results.append(item)
    return results


def list_all_content(brand: Optional[str] = None, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all content records regardless of status."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    query = "SELECT * FROM content_queue"
    params: List[Any] = []
    if brand:
        query += " WHERE brand = ?"
        params.append(brand)
    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    results = []
    for row in rows:
        item = dict(row)
        for field in ["compliance_result", "sources"]:
            if item.get(field):
                try:
                    item[field] = json.loads(item[field])
                except Exception:
                    pass
        results.append(item)
    return results


def update_compliance_result(content_id: int, compliance_result: Dict[str, Any], db_path: Optional[str] = None) -> None:
    """Update compliance result for an existing content queue record."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE content_queue SET compliance_result = ? WHERE id = ?",
        (json.dumps(compliance_result), content_id),
    )
    conn.commit()
    conn.close()


# =====================================================================
# Governance & Human Review State Transitions
# =====================================================================

def approve_content(content_id: int, db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Approve content by human reviewer.
    RULE: Content can only be approved if it is currently 'pending'.
    Direct agent-to-approved transitions are strictly disallowed.
    """
    item = get_content_by_id(content_id, db_path=db_path)
    if not item:
        raise ValueError(f"Content ID {content_id} not found.")

    if item["status"] not in ("pending", "rejected"):
        raise ValueError(f"Cannot approve content currently in '{item['status']}' state.")

    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE content_queue SET status = 'approved' WHERE id = ?", (content_id,))
    conn.commit()
    conn.close()

    return get_content_by_id(content_id, db_path=db_path)  # type: ignore


def reject_content(
    content_id: int,
    tag: str,
    note: str,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Reject content with human feedback.
    RULE: Tag must be valid, Note must not be empty.
    Stores immutable feedback in feedback table and updates status to 'rejected'.
    Original content is preserved in content_queue.
    """
    if tag not in VALID_FEEDBACK_TAGS:
        raise ValueError(f"Invalid tag '{tag}'. Must be one of: {sorted(VALID_FEEDBACK_TAGS)}")

    clean_note = (note or "").strip()
    if not clean_note:
        raise ValueError("A free-text feedback note is required for rejections.")

    item = get_content_by_id(content_id, db_path=db_path)
    if not item:
        raise ValueError(f"Content ID {content_id} not found.")

    conn = get_connection(db_path)
    cursor = conn.cursor()

    # 1. Update status
    cursor.execute("UPDATE content_queue SET status = 'rejected' WHERE id = ?", (content_id,))

    # 2. Insert feedback record
    cursor.execute(
        "INSERT INTO feedback (content_id, brand, tag, note) VALUES (?, ?, ?, ?)",
        (content_id, item["brand"], tag, clean_note),
    )

    conn.commit()
    conn.close()

    return get_content_by_id(content_id, db_path=db_path)  # type: ignore


def edit_content(
    content_id: int,
    edited_content: str,
    tag: Optional[str] = None,
    note: Optional[str] = None,
    compliance_result: Optional[Dict[str, Any]] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Allow human reviewer to edit content directly.
    Optionally records edit reason in feedback table.
    """
    clean_content = (edited_content or "").strip()
    if not clean_content:
        raise ValueError("Edited content cannot be empty.")

    item = get_content_by_id(content_id, db_path=db_path)
    if not item:
        raise ValueError(f"Content ID {content_id} not found.")

    conn = get_connection(db_path)
    cursor = conn.cursor()

    comp_str = json.dumps(compliance_result) if compliance_result else item.get("compliance_result")
    if isinstance(comp_str, dict):
        comp_str = json.dumps(comp_str)

    cursor.execute(
        "UPDATE content_queue SET content = ?, compliance_result = ? WHERE id = ?",
        (clean_content, comp_str, content_id),
    )

    if tag and note and note.strip():
        cursor.execute(
            "INSERT INTO feedback (content_id, brand, tag, note) VALUES (?, ?, ?, ?)",
            (content_id, item["brand"], tag, note.strip()),
        )

    conn.commit()
    conn.close()

    return get_content_by_id(content_id, db_path=db_path)  # type: ignore


def schedule_content(content_id: int, db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Transition content to 'scheduled' state for social posting worker.
    RULE: Content can ONLY reach 'scheduled' if it was ALREADY 'approved'!
    Enforced at database layer as required by 03_Security_Access.md.
    """
    item = get_content_by_id(content_id, db_path=db_path)
    if not item:
        raise ValueError(f"Content ID {content_id} not found.")

    if item["status"] != "approved":
        raise ValueError(
            f"Security Rule Violation: Content must be 'approved' before scheduling. Current status is '{item['status']}'."
        )

    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE content_queue SET status = 'scheduled' WHERE id = ?", (content_id,))
    conn.commit()
    conn.close()

    return get_content_by_id(content_id, db_path=db_path)  # type: ignore


# =====================================================================
# Feedback & Learning Queries
# =====================================================================

def get_recent_feedback(brand: str, n: int = 5, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieve the last N human feedback notes for a brand.
    Used by Content Agent to inject few-shot corrections into prompt.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT f.id, f.content_id, f.brand, f.tag, f.note, f.created_at, cq.content as original_content
        FROM feedback f
        JOIN content_queue cq ON f.content_id = cq.id
        WHERE f.brand = ?
        ORDER BY f.created_at DESC, f.id DESC
        LIMIT ?
        """,
        (brand, n),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_all_feedback(brand: Optional[str] = None, limit: int = 100, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """List feedback records with linked content snippets."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    query = """
        SELECT f.id, f.content_id, f.brand, f.tag, f.note, f.created_at, cq.content as original_content, cq.platform
        FROM feedback f
        LEFT JOIN content_queue cq ON f.content_id = cq.id
    """
    params: List[Any] = []
    if brand:
        query += " WHERE f.brand = ?"
        params.append(brand)
    query += " ORDER BY f.created_at DESC, f.id DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_rejection_rate_by_cycle(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Calculate rejection rate per generation/review cycle based on real database records.
    Returns: [{'cycle': 1, 'total': 10, 'rejected': 8, 'approved': 2, 'rejection_rate': 80.0}, ...]
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT 
            cycle,
            COUNT(*) as total_reviewed,
            SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected_count,
            SUM(CASE WHEN status IN ('approved', 'scheduled') THEN 1 ELSE 0 END) as approved_count
        FROM content_queue
        WHERE status IN ('rejected', 'approved', 'scheduled')
        GROUP BY cycle
        ORDER BY cycle ASC
        """
    )
    rows = cursor.fetchall()
    conn.close()

    stats = []
    for row in rows:
        total = row["total_reviewed"]
        rej = row["rejected_count"] or 0
        app = row["approved_count"] or 0
        rate = round((rej / total * 100), 1) if total > 0 else 0.0
        stats.append({
            "cycle": row["cycle"],
            "total": total,
            "rejected": rej,
            "approved": app,
            "rejection_rate": rate,
        })
    return stats


def get_before_after_pairs(brand: Optional[str] = None, limit: int = 10, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieve before/after comparisons where regenerated content (child) links to parent_id.
    Visually showcases the learning loop: original rejected vs. regenerated compliant copy.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    query = """
        SELECT 
            child.id as child_id,
            child.brand,
            child.platform,
            child.content_type,
            child.content as regenerated_content,
            child.status as child_status,
            child.compliance_result as child_compliance,
            child.fixed_issue,
            child.sources as child_sources,
            child.created_at as child_created_at,
            parent.id as parent_id,
            parent.content as original_content,
            parent.compliance_result as parent_compliance,
            parent.sources as parent_sources,
            f.tag as feedback_tag,
            f.note as feedback_note
        FROM content_queue child
        JOIN content_queue parent ON child.parent_id = parent.id
        LEFT JOIN feedback f ON f.content_id = parent.id
        WHERE child.parent_id IS NOT NULL
    """
    params: List[Any] = []
    if brand:
        query += " AND child.brand = ?"
        params.append(brand)

    query += " ORDER BY child.created_at DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    pairs = []
    for row in rows:
        item = dict(row)
        for field in ["child_compliance", "parent_compliance", "child_sources", "parent_sources"]:
            if item.get(field):
                try:
                    item[field] = json.loads(item[field])
                except Exception:
                    pass
        pairs.append(item)
    return pairs


# =====================================================================
# Leads Operations (P1)
# =====================================================================

def insert_lead(
    name: str,
    contact: str,
    vertical: str,
    fit_score: int,
    outreach_draft: str,
    status: str = "new",
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Insert a prospective InsurTech lead."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO leads (name, contact, vertical, fit_score, outreach_draft, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (name, contact, vertical, fit_score, outreach_draft, status),
    )
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"id": new_id, "name": name, "contact": contact, "vertical": vertical, "fit_score": fit_score, "status": status}


def list_leads(vertical: Optional[str] = None, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """List prospect leads for sales team outreach."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    query = "SELECT * FROM leads"
    params: List[Any] = []
    if vertical:
        query += " WHERE vertical = ?"
        params.append(vertical)
    query += " ORDER BY fit_score DESC, id DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_lead_status(lead_id: int, status: str, db_path: Optional[str] = None) -> None:
    """Update lead status (new, contacted, qualified)."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE leads SET status = ? WHERE id = ?", (status, lead_id))
    conn.commit()
    conn.close()
