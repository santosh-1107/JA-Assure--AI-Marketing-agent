"""
Data models and CRUD operations for JA Assure AI Marketing Agent.
Strictly enforces compliance state machines, human review governance,
and non-destructive metadata tracking.
"""

import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from backend.database import get_connection

VALID_FEEDBACK_TAGS = {
    "too_salesy",
    "inaccurate_claim",
    "off_brand_tone",
    "wrong_cta",
    "unsupported_claim",
    "unsupported_guarantee",
    "missing_qualifier",
    "aggressive_urgency",
    "human_edit",
    "other",
}

VALID_STATUSES = {"pending", "approved", "rejected", "scheduled"}
VALID_BRANDS = {"Jade", "DoctorShield"}
VALID_PLATFORMS = {"LinkedIn", "Instagram", "X"}
VALID_CONTENT_TYPES = {"post", "carousel", "tweet", "video_script"}


def _deserialize_item(row_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Safely deserialize JSON string fields into python dicts/lists."""
    json_fields = [
        "compliance_result",
        "sources",
        "generation_metadata",
        "knowledge_source_ids",
        "feedback_ids",
        "scoring_breakdown",
        "child_compliance",
        "parent_compliance",
        "child_sources",
        "parent_sources",
    ]
    for field in json_fields:
        val = row_dict.get(field)
        if val and isinstance(val, str):
            try:
                row_dict[field] = json.loads(val)
            except Exception:
                pass
    return row_dict


# =====================================================================
# Content Queue Operations
# =====================================================================

def insert_content(
    brand: str,
    platform: str,
    content_type: str,
    content: str,
    topic: Optional[str] = None,
    product: Optional[str] = None,
    compliance_result: Optional[Dict[str, Any]] = None,
    cycle: int = 1,
    parent_id: Optional[int] = None,
    fixed_issue: Optional[str] = None,
    sources: Optional[List[Dict[str, Any]]] = None,
    generation_mode: str = "offline",
    provider: Optional[str] = None,
    model: str = "offline-engine",
    prompt_version: str = "1.0",
    knowledge_source_ids: Optional[List[str]] = None,
    feedback_ids: Optional[List[int]] = None,
    generation_metadata: Optional[Dict[str, Any]] = None,
    risk_level: Optional[str] = None,
    risk_score: Optional[float] = None,
    status: str = "pending",
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Insert a newly generated marketing asset into the content_queue.
    Defaults to status='pending' requiring human review.
    Attaches verified JA Assure knowledge sources and generation metadata.
    """
    if brand not in VALID_BRANDS:
        raise ValueError(f"Validation Error: Invalid brand '{brand}'. Must be one of: {sorted(VALID_BRANDS)}")
    if platform not in VALID_PLATFORMS:
        raise ValueError(f"Validation Error: Invalid platform '{platform}'. Must be one of: {sorted(VALID_PLATFORMS)}")
    if content_type not in VALID_CONTENT_TYPES:
        raise ValueError(f"Validation Error: Invalid content_type '{content_type}'. Must be one of: {sorted(VALID_CONTENT_TYPES)}")
    if status not in VALID_STATUSES:
        raise ValueError(f"Validation Error: Invalid status '{status}'. Must be one of: {sorted(VALID_STATUSES)}")

    conn = get_connection(db_path)
    cursor = conn.cursor()

    comp_str = json.dumps(compliance_result) if compliance_result else None
    sources_str = json.dumps(sources) if sources else None
    meta_str = json.dumps(generation_metadata) if generation_metadata else None
    src_ids_str = json.dumps(knowledge_source_ids) if knowledge_source_ids else None
    fb_ids_str = json.dumps(feedback_ids) if feedback_ids else None

    # Derive risk metrics from compliance_result if not explicitly provided
    resolved_risk_level = risk_level
    resolved_risk_score = risk_score
    if compliance_result and isinstance(compliance_result, dict):
        if resolved_risk_level is None:
            resolved_risk_level = compliance_result.get("risk_level", "LOW")
        if resolved_risk_score is None:
            resolved_risk_score = float(compliance_result.get("risk_score", 0.0))

    resolved_provider = provider or generation_mode

    cursor.execute(
        """
        INSERT INTO content_queue (
            brand, platform, content_type, topic, product, content, status, compliance_result,
            cycle, parent_id, fixed_issue, sources, generation_mode, provider, model,
            prompt_version, knowledge_source_ids, feedback_ids, generation_metadata,
            risk_level, risk_score
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            brand,
            platform,
            content_type,
            topic,
            product,
            content,
            status,
            comp_str,
            cycle,
            parent_id,
            fixed_issue,
            sources_str,
            generation_mode,
            resolved_provider,
            model,
            prompt_version,
            src_ids_str,
            fb_ids_str,
            meta_str,
            resolved_risk_level,
            resolved_risk_score,
        ),
    )
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return get_content_by_id(new_id, db_path=db_path)  # type: ignore


def get_content_by_id(content_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Fetch a single content queue item by ID with deserialized metadata."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM content_queue WHERE id = ?", (content_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return _deserialize_item(dict(row))


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

    return [_deserialize_item(dict(r)) for r in rows]


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

    return [_deserialize_item(dict(r)) for r in rows]


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

    return [_deserialize_item(dict(r)) for r in rows]


def update_compliance_result(content_id: int, compliance_result: Dict[str, Any], db_path: Optional[str] = None) -> None:
    """Update compliance result for an existing content queue record."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE content_queue SET compliance_result = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
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
    STRICT GOVERNANCE RULES (Phase 7):
    1. Content must exist.
    2. Content MUST be currently in 'pending' status (rejected or approved items cannot be approved).
    3. Compliance result status MUST be 'pass' (failing items cannot be approved).
    """
    item = get_content_by_id(content_id, db_path=db_path)
    if not item:
        raise ValueError(f"Content ID {content_id} not found.")

    if item["status"] != "pending":
        raise ValueError(
            f"State Machine Violation: Cannot approve content currently in '{item['status']}' state. "
            "Only 'pending' content can be approved."
        )

    comp = item.get("compliance_result") or {}
    if comp.get("status") != "pass":
        raise ValueError(
            f"Compliance Governance Violation: Content ID {content_id} has not passed compliance checks "
            f"(status='{comp.get('status', 'unknown')}') and cannot be approved."
        )

    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE content_queue SET status = 'approved', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (content_id,))
    conn.commit()
    conn.close()

    return get_content_by_id(content_id, db_path=db_path)  # type: ignore


def reject_content(
    content_id: int,
    tag: str,
    note: str,
    issue_type: Optional[str] = None,
    corrected_content: Optional[str] = None,
    risk_score: Optional[float] = None,
    compliance_rule: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Reject content with human feedback.
    STRICT GOVERNANCE RULES (Phase 7):
    1. Content must exist.
    2. Content MUST be in 'pending' status.
    3. Tag must be valid, Note must not be empty.
    Stores immutable structured feedback in feedback table, indexes into vector store,
    and updates status to 'rejected'. Original content is preserved in content_queue.
    """
    if tag not in VALID_FEEDBACK_TAGS:
        raise ValueError(f"Invalid tag '{tag}'. Must be one of: {sorted(VALID_FEEDBACK_TAGS)}")

    clean_note = (note or "").strip()
    if not clean_note:
        raise ValueError("A free-text feedback note is required for rejections.")

    item = get_content_by_id(content_id, db_path=db_path)
    if not item:
        raise ValueError(f"Content ID {content_id} not found.")

    if item["status"] != "pending":
        raise ValueError(
            f"State Machine Violation: Cannot reject content currently in '{item['status']}' state. "
            "Only 'pending' content can be rejected."
        )

    resolved_issue_type = issue_type or tag
    orig_content = item.get("content", "")
    prod = item.get("product")
    plat = item.get("platform")

    # Derive compliance rule and risk score from item if not explicitly supplied
    comp_res = item.get("compliance_result") or {}
    resolved_risk_score = risk_score
    if resolved_risk_score is None and isinstance(comp_res, dict):
        resolved_risk_score = float(comp_res.get("risk_score", 30.0))

    resolved_rule = compliance_rule
    if not resolved_rule and isinstance(comp_res, dict):
        reasons = comp_res.get("reasons") or comp_res.get("issues") or []
        if reasons:
            first_r = reasons[0]
            resolved_rule = first_r.get("rule") or first_r.get("rule_id", "GENERAL_REGULATORY")

    conn = get_connection(db_path)
    cursor = conn.cursor()

    # 1. Update status to rejected
    cursor.execute("UPDATE content_queue SET status = 'rejected', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (content_id,))

    # 2. Insert structured feedback record
    cursor.execute(
        """
        INSERT INTO feedback (
            content_id, brand, tag, note, original_content, corrected_content,
            issue_type, product, platform, risk_score, compliance_rule
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            content_id,
            item["brand"],
            tag,
            clean_note,
            orig_content,
            corrected_content,
            resolved_issue_type,
            prod,
            plat,
            resolved_risk_score,
            resolved_rule,
        ),
    )
    feedback_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # 3. Create embedding and store in vector store collection 'feedback_embeddings'
    try:
        from backend.knowledge.vector_store import vector_store
        vector_store.index_feedback(
            feedback_id=feedback_id,
            content_id=content_id,
            original_content=orig_content,
            corrected_content=corrected_content,
            issue_type=resolved_issue_type,
            rejection_tag=tag,
            reviewer_note=clean_note,
            brand=item["brand"],
            product=prod,
            platform=plat,
            risk_score=resolved_risk_score,
            compliance_rule=resolved_rule,
        )
    except Exception as e:
        # Non-fatal if vector store encounters transient lock in tests
        pass

    return get_content_by_id(content_id, db_path=db_path)  # type: ignore


def edit_content(
    content_id: int,
    edited_content: str,
    tag: Optional[str] = None,
    note: Optional[str] = None,
    issue_type: Optional[str] = None,
    risk_score: Optional[float] = None,
    compliance_rule: Optional[str] = None,
    compliance_result: Optional[Dict[str, Any]] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Allow human reviewer to edit content directly.
    CRITICAL GOVERNANCE RULES:
    1. Persist the edited content to SQLite under the content_id.
    2. Invalidate previous compliance verdict because content changed.
    3. Re-run Compliance/Risk Agent against the edited content.
    4. Store new compliance result, risk level, and risk score.
    5. Reset status = 'pending' unconditionally so it cannot bypass review.
    6. Preserve original content in both generation_metadata and feedback table.
    7. Record that a human edit occurred in feedback audit trail.
    8. Index the correction in vector store for semantic learning.
    """
    clean_content = (edited_content or "").strip()
    if not clean_content:
        raise ValueError("Edited content cannot be empty.")
    if len(clean_content) < 5:
        raise ValueError("Edited content must be at least 5 characters.")

    item = get_content_by_id(content_id, db_path=db_path)
    if not item:
        raise ValueError(f"Content ID {content_id} not found.")

    # Invalidate previous compliance and re-evaluate compliance on edited copy
    if not compliance_result or not isinstance(compliance_result, dict) or "status" not in compliance_result:
        from backend.agents.compliance_agent import compliance_agent
        compliance_result = compliance_agent.check(clean_content, item["brand"])

    comp_str = json.dumps(compliance_result)
    new_status = compliance_result.get("status", "pass").lower()
    resolved_risk_score = float(risk_score if risk_score is not None else compliance_result.get("risk_score", 0.0))
    resolved_risk_level = compliance_result.get("risk_level", "LOW")

    # Record edit history and preserve original content in generation_metadata
    clean_note = (note or "").strip() or "Human reviewer modified marketing copy directly."
    tag_to_use = tag if (tag and tag in VALID_FEEDBACK_TAGS) else ("inaccurate_claim" if new_status == "fail" else "human_edit")
    resolved_issue_type = issue_type or tag_to_use

    meta = dict(item.get("generation_metadata") or {})
    edit_history = meta.get("edit_history") or []
    edit_history.append({
        "timestamp": datetime.now().isoformat(),
        "previous_content": item["content"],
        "previous_compliance": item.get("compliance_result"),
        "previous_risk_score": item.get("risk_score", 0.0),
        "previous_status": item.get("status", "pending"),
        "note": clean_note,
        "tag": tag_to_use,
    })
    meta["edit_history"] = edit_history
    meta["human_edited"] = True
    meta["original_content"] = meta.get("original_content") or item["content"]
    meta["last_edited_at"] = datetime.now().isoformat()
    meta_str = json.dumps(meta)

    fixed_note = f"Human edit: {clean_note}"

    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Update content_queue record
    cursor.execute(
        """
        UPDATE content_queue 
        SET content = ?,
            compliance_result = ?,
            risk_level = ?,
            risk_score = ?,
            status = 'pending',
            fixed_issue = ?,
            generation_metadata = ?,
            updated_at = CURRENT_TIMESTAMP 
        WHERE id = ?
        """,
        (
            clean_content,
            comp_str,
            resolved_risk_level,
            resolved_risk_score,
            fixed_note,
            meta_str,
            content_id,
        ),
    )

    # Always record that a human edit occurred in feedback audit trail
    resolved_rule = compliance_rule
    if not resolved_rule and compliance_result.get("reasons"):
        resolved_rule = compliance_result["reasons"][0].get("rule")

    cursor.execute(
        """
        INSERT INTO feedback (
            content_id, brand, tag, note, original_content, corrected_content,
            issue_type, product, platform, risk_score, compliance_rule
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            content_id,
            item["brand"],
            tag_to_use,
            clean_note,
            item["content"],
            clean_content,
            resolved_issue_type,
            item.get("product"),
            item.get("platform"),
            resolved_risk_score,
            resolved_rule,
        ),
    )
    feedback_id = cursor.lastrowid

    conn.commit()
    conn.close()

    # Create vector embedding for semantic learning
    if feedback_id:
        try:
            from backend.knowledge.vector_store import vector_store
            vector_store.index_feedback(
                feedback_id=feedback_id,
                content_id=content_id,
                original_content=item["content"],
                corrected_content=clean_content,
                issue_type=resolved_issue_type,
                rejection_tag=tag_to_use,
                reviewer_note=clean_note,
                brand=item["brand"],
                product=item.get("product"),
                platform=item.get("platform"),
                risk_score=resolved_risk_score,
                compliance_rule=resolved_rule,
            )
        except Exception:
            pass

    return get_content_by_id(content_id, db_path=db_path)  # type: ignore


def schedule_content(content_id: int, db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Transition content to 'scheduled' state.
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
    cursor.execute("UPDATE content_queue SET status = 'scheduled', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (content_id,))
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
        SELECT f.id, f.content_id, f.brand, f.tag, f.note, f.original_content, f.corrected_content,
               f.issue_type, f.product, f.platform, f.risk_score, f.compliance_rule, f.created_at,
               cq.content as queue_content
        FROM feedback f
        JOIN content_queue cq ON f.content_id = cq.id
        WHERE f.brand = ?
        ORDER BY f.id DESC
        LIMIT ?
        """,
        (brand, n),
    )
    rows = cursor.fetchall()
    conn.close()

    results = []
    for r in rows:
        d = dict(r)
        # Fallback for original_content
        if not d.get("original_content"):
            d["original_content"] = d.get("queue_content", "")
        results.append(d)
    return results


def list_all_feedback(limit: int = 50, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all human feedback notes across brands for the audit trail."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT f.id, f.content_id, f.brand, f.tag, f.note, f.original_content, f.corrected_content,
               f.issue_type, f.product, f.platform, f.risk_score, f.compliance_rule, f.created_at,
               cq.platform as queue_platform
        FROM feedback f
        LEFT JOIN content_queue cq ON f.content_id = cq.id
        ORDER BY f.id DESC
        LIMIT ?
        """,
        (limit,),
    )
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
            child.topic,
            child.content as regenerated_content,
            child.status as child_status,
            child.compliance_result as child_compliance,
            child.fixed_issue,
            child.sources as child_sources,
            child.generation_mode as child_generation_mode,
            child.created_at as child_created_at,
            parent.id as parent_id,
            parent.topic as parent_topic,
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

    return [_deserialize_item(dict(r)) for r in rows]


# =====================================================================
# Leads Operations
# =====================================================================

def insert_lead(
    name: str,
    contact: Optional[str],
    vertical: str,
    fit_score: int,
    outreach_draft: Optional[str] = None,
    region: str = "Singapore",
    source: Optional[str] = None,
    source_url: Optional[str] = None,
    scoring_breakdown: Optional[Dict[str, Any]] = None,
    status: str = "new",
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Insert a prospective InsurTech lead with explicit scoring factors."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    breakdown_str = json.dumps(scoring_breakdown) if scoring_breakdown else None

    cursor.execute(
        """
        INSERT INTO leads (name, contact, vertical, region, fit_score, outreach_draft, source, source_url, scoring_breakdown, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (name, contact, vertical, region, fit_score, outreach_draft, source, source_url, breakdown_str, status),
    )
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {
        "id": new_id,
        "name": name,
        "contact": contact,
        "vertical": vertical,
        "region": region,
        "fit_score": fit_score,
        "outreach_draft": outreach_draft,
        "source": source,
        "source_url": source_url,
        "scoring_breakdown": scoring_breakdown,
        "status": status,
    }


def list_leads(
    vertical: Optional[str] = None,
    region: Optional[str] = None,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List prospect leads for sales team outreach."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    query = "SELECT * FROM leads WHERE 1=1"
    params: List[Any] = []
    if vertical and vertical != "All Verticals":
        query += " AND vertical = ?"
        params.append(vertical)
    if region:
        query += " AND region = ?"
        params.append(region)
    query += " ORDER BY fit_score DESC, id DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [_deserialize_item(dict(r)) for r in rows]


def update_lead_status(lead_id: int, status: str, db_path: Optional[str] = None) -> None:
    """Update lead status (new, contacted, qualified)."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE leads SET status = ? WHERE id = ?", (status, lead_id))
    conn.commit()
    conn.close()
