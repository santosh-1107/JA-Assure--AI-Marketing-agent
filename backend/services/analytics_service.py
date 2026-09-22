"""
Centralized Analytics Service for JA Assure AI Marketing Agent.
Derives all operational metrics, review counts, rejection trends, and learning rates
strictly from actual SQLite records. Never invents or hardcodes fallback metrics.
"""

from typing import Any, Dict, List, Optional
from backend.database import get_connection
from backend.models import get_rejection_rate_by_cycle
from backend.knowledge.ja_assure_sources import load_all_sources


def get_dashboard_metrics(db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Derive comprehensive operational dashboard KPIs directly from SQLite.
    Returns None or 0.0 when data does not exist; never falls back to arbitrary numbers.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # 1. Content counts by status
    cursor.execute("""
        SELECT 
            COUNT(*) as total_assets,
            SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_count,
            SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved_count,
            SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected_count,
            SUM(CASE WHEN status = 'scheduled' THEN 1 ELSE 0 END) as scheduled_count
        FROM content_queue
    """)
    cq_row = cursor.fetchone()
    total_assets = cq_row["total_assets"] or 0
    pending_count = cq_row["pending_count"] or 0
    approved_count = cq_row["approved_count"] or 0
    rejected_count = cq_row["rejected_count"] or 0
    scheduled_count = cq_row["scheduled_count"] or 0

    # 2. Total feedback items
    cursor.execute("SELECT COUNT(*) FROM feedback")
    total_feedback = cursor.fetchone()[0] or 0

    # 3. Total leads
    cursor.execute("SELECT COUNT(*) FROM leads")
    lead_count = cursor.fetchone()[0] or 0

    conn.close()

    # Total reviewed items (excluding pending)
    total_reviewed = approved_count + scheduled_count + rejected_count
    overall_rejection_rate = (
        round((rejected_count / total_reviewed) * 100, 1) if total_reviewed > 0 else 0.0
    )
    approval_rate = (
        round(((approved_count + scheduled_count) / total_reviewed) * 100, 1) if total_reviewed > 0 else 0.0
    )

    # 4. Cycle metrics from actual database records
    cycle_stats = get_rejection_rate_by_cycle(db_path=db_path)
    latest_cycle = cycle_stats[-1]["cycle"] if cycle_stats else None
    latest_cycle_rejection_rate = cycle_stats[-1]["rejection_rate"] if cycle_stats else None
    previous_cycle_rejection_rate = (
        cycle_stats[-2]["rejection_rate"] if len(cycle_stats) >= 2 else None
    )
    baseline_rejection_rate = cycle_stats[0]["rejection_rate"] if cycle_stats else None

    # Calculate real relative error reduction if at least 2 cycles exist
    relative_error_reduction = None
    rejection_rate_delta = None
    if len(cycle_stats) >= 2 and cycle_stats[0]["rejection_rate"] > 0:
        c1_rate = cycle_stats[0]["rejection_rate"]
        latest_rate = cycle_stats[-1]["rejection_rate"]
        relative_error_reduction = round(((c1_rate - latest_rate) / c1_rate) * 100, 1)
        rejection_rate_delta = round(latest_rate - c1_rate, 1)

    knowledge_sources = load_all_sources()

    return {
        "pending_count": pending_count,
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "scheduled_count": scheduled_count,
        "total_assets": total_assets,
        "total_feedback": total_feedback,
        "total_reviewed": total_reviewed,
        "overall_rejection_rate": overall_rejection_rate,
        "approval_rate": approval_rate,
        "latest_cycle": latest_cycle,
        "latest_cycle_rejection_rate": latest_cycle_rejection_rate,
        "previous_cycle_rejection_rate": previous_cycle_rejection_rate,
        "baseline_rejection_rate": baseline_rejection_rate,
        "relative_error_reduction": relative_error_reduction,
        "rejection_rate_delta": rejection_rate_delta,
        "learning_corrections": total_feedback,
        "knowledge_source_count": len(knowledge_sources),
        "lead_count": lead_count,
        "cycles": cycle_stats,
    }


def get_cycle_metrics(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return array of review metrics per cycle from actual content_queue rows."""
    return get_rejection_rate_by_cycle(db_path=db_path)


def get_trend_metrics(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Compute real trend deltas between the latest and prior review cycles."""
    cycles = get_rejection_rate_by_cycle(db_path=db_path)
    if not cycles or len(cycles) < 2:
        return {
            "has_trend": False,
            "latest_rate": cycles[0]["rejection_rate"] if cycles else 0.0,
            "prior_rate": None,
            "delta_points": None,
            "relative_reduction_pct": None,
        }

    c_latest = cycles[-1]
    c_prior = cycles[-2]
    delta = round(c_latest["rejection_rate"] - c_prior["rejection_rate"], 1)
    rel_reduction = (
        round(((c_prior["rejection_rate"] - c_latest["rejection_rate"]) / c_prior["rejection_rate"]) * 100, 1)
        if c_prior["rejection_rate"] > 0
        else 0.0
    )

    return {
        "has_trend": True,
        "latest_rate": c_latest["rejection_rate"],
        "prior_rate": c_prior["rejection_rate"],
        "delta_points": delta,
        "relative_reduction_pct": rel_reduction,
    }


def get_learning_metrics(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Summary of closed-loop learning and few-shot constraints."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT tag, COUNT(*) as tag_count FROM feedback GROUP BY tag ORDER BY tag_count DESC")
    tag_counts = {row["tag"]: row["tag_count"] for row in cursor.fetchall()}

    cursor.execute("SELECT COUNT(*) FROM content_queue WHERE parent_id IS NOT NULL")
    variant_pairs_count = cursor.fetchone()[0] or 0

    conn.close()

    cycle_stats = get_rejection_rate_by_cycle(db_path=db_path)

    return {
        "tag_breakdown": tag_counts,
        "variant_pairs_count": variant_pairs_count,
        "cycles": cycle_stats,
    }


def get_risk_heatmap(db_path: Optional[str] = None, group_by: str = "brand") -> Dict[str, Any]:
    """
    Compute dynamic risk heatmap matrix from actual database records.
    Rows: Risk issue types (e.g. unsupported_guarantee, inaccurate_claim, off_brand_tone, aggressive_urgency, missing_qualifier)
    Columns: Brands ('Jade', 'DoctorShield') or Platforms ('LinkedIn', 'Instagram', 'X')
    Values: Actual occurrence counts aggregated from feedback and non-compliant content items.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    columns = ["Jade", "DoctorShield"] if group_by == "brand" else ["LinkedIn", "Instagram", "X"]
    standard_issue_types = [
        "inaccurate_claim",
        "unsupported_guarantee",
        "missing_qualifier",
        "aggressive_urgency",
        "off_brand_tone",
        "unsupported_legal_claim",
        "other",
    ]

    # Matrix: {issue_type: {col: count}}
    matrix: Dict[str, Dict[str, int]] = {it: {col: 0 for col in columns} for it in standard_issue_types}

    # 1. Tally from feedback table
    col_field = "f.brand" if group_by == "brand" else "cq.platform"
    cursor.execute(f"""
        SELECT 
            COALESCE(f.issue_type, f.tag) as issue,
            {col_field} as col_val,
            COUNT(*) as cnt
        FROM feedback f
        LEFT JOIN content_queue cq ON f.content_id = cq.id
        GROUP BY issue, col_val
    """)
    for row in cursor.fetchall():
        raw_issue = (row["issue"] or "other").lower().replace(" ", "_")
        col_val = row["col_val"]

        # Map to standard issue type if needed
        matched_issue = "other"
        for st_it in standard_issue_types:
            if st_it in raw_issue or raw_issue in st_it:
                matched_issue = st_it
                break

        if matched_issue not in matrix:
            matrix[matched_issue] = {c: 0 for c in columns}

        if col_val in columns:
            matrix[matched_issue][col_val] += int(row["cnt"])

    # 2. Tally from non-compliant content_queue items that recorded compliance issues
    cq_col = "brand" if group_by == "brand" else "platform"
    cursor.execute(f"""
        SELECT {cq_col} as col_val, compliance_result
        FROM content_queue
        WHERE compliance_result IS NOT NULL AND status IN ('rejected', 'pending')
    """)
    import json
    for row in cursor.fetchall():
        col_val = row["col_val"]
        if col_val not in columns:
            continue
        comp_raw = row["compliance_result"]
        if not comp_raw:
            continue
        try:
            comp_data = json.loads(comp_raw) if isinstance(comp_raw, str) else comp_raw
            issues = comp_data.get("issues") or []
            reasons = comp_data.get("reasons") or []
            # Extract issue types from issues or reasons
            for iss in issues:
                itype = iss.get("issue_type", "other")
                if itype in matrix:
                    matrix[itype][col_val] += 1
            if not issues and reasons:
                for r in reasons:
                    rule = r.get("rule", "").lower()
                    if "payout" in rule or "guarantee" in rule:
                        matrix["unsupported_guarantee"][col_val] += 1
                    elif "protect" in rule or "100" in rule:
                        matrix["inaccurate_claim"][col_val] += 1
                    elif "qualif" in rule:
                        matrix["missing_qualifier"][col_val] += 1
                    elif "tone" in rule or "brand" in rule:
                        matrix["off_brand_tone"][col_val] += 1
                    elif "scare" in rule or "sales" in rule:
                        matrix["aggressive_urgency"][col_val] += 1
        except Exception:
            pass

    conn.close()

    # Format rows for table / heatmap visualization
    heatmap_rows = []
    total_violations = 0
    for itype in standard_issue_types:
        row_data = {"issue_type": itype}
        row_sum = 0
        for col in columns:
            val = matrix[itype].get(col, 0)
            row_data[col] = val
            row_sum += val
        row_data["total"] = row_sum
        total_violations += row_sum
        heatmap_rows.append(row_data)

    return {
        "group_by": group_by,
        "columns": columns,
        "rows": heatmap_rows,
        "total_violations": total_violations,
    }


def get_top_recurring_issues(db_path: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
    """Return top recurring compliance violations calculated from feedback records."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            COALESCE(issue_type, tag) as issue,
            COUNT(*) as frequency
        FROM feedback
        GROUP BY issue
        ORDER BY frequency DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()

    total_count = sum(r["frequency"] for r in rows) if rows else 1
    results = []
    for r in rows:
        freq = r["frequency"]
        pct = round((freq / total_count) * 100, 1) if total_count > 0 else 0.0
        results.append({
            "issue": r["issue"],
            "issue_type": r["issue"],
            "frequency": freq,
            "percentage": pct,
        })
    return results


def get_risk_distribution(db_path: Optional[str] = None) -> Dict[str, int]:
    """Return count of generated content assets distributed by risk level."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            COALESCE(risk_level, 'LOW') as r_level,
            COUNT(*) as count
        FROM content_queue
        GROUP BY r_level
    """)
    rows = cursor.fetchall()
    conn.close()

    dist = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    for r in rows:
        lvl = (r["r_level"] or "LOW").upper()
        if lvl in dist:
            dist[lvl] += r["count"]
    return dist

