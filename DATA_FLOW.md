# JA Assure AI Marketing Agent — Data Flow Specification

## 1. End-to-End Generation & Review Flow

The diagram below details the sequence of data transformations from initial brief entry to final scheduling:

```mermaid
sequenceDiagram
    autonumber
    actor Reviewer as Human Reviewer
    participant UI as Streamlit Dashboard
    participant API as FastAPI Backend
    participant RA as Research Agent
    participant FA as Feedback Agent
    participant CA as Content Agent
    participant COMP as Compliance Agent
    participant DB as SQLite (content_queue & feedback)

    Reviewer->>UI: Enter Topic, Brand, Platform
    UI->>API: POST /content/generate
    
    API->>RA: research(brand, topic, competitor_list)
    RA-->>API: {summary, sources, recommendations}
    
    API->>FA: get_recent_feedback(brand, n=5)
    FA->>DB: Query last 5 feedback rows for brand
    DB-->>FA: [FeedbackItem, ...]
    FA-->>API: formatted few-shot constraints
    
    API->>CA: generate(topic, brand, platform, research, feedback)
    CA-->>API: {content, metadata, sources}
    
    API->>COMP: check(content, brand)
    COMP-->>API: {status: "pass"|"fail", reasons: [...]}
    
    API->>DB: insert_content(status="pending", compliance, metadata)
    DB-->>API: Saved Content Item (#ID)
    API-->>UI: Return ContentItemResponse
    UI-->>Reviewer: Display in Review Queue (Card marked PASS or FAIL)
```

---

## 2. Human Rejection & Stored Feedback Flow

When an asset is flagged for non-compliance or off-brand tone:

```mermaid
sequenceDiagram
    autonumber
    actor Reviewer as Human Reviewer
    participant UI as Streamlit Dashboard
    participant API as FastAPI Backend
    participant DB as SQLite (content_queue & feedback)

    Reviewer->>UI: Click "✕ Reject" with tag and note
    UI->>API: POST /content/{id}/reject {tag, note}
    API->>DB: UPDATE content_queue SET status='rejected' WHERE id={id}
    API->>DB: INSERT INTO feedback (content_id, brand, tag, note)
    DB-->>API: Confirmation
    API-->>UI: Updated Content Item (status: rejected)
    UI-->>Reviewer: Shows rejection confirmed; feedback stored immutably
```

---

## 3. Closed-Loop Feedback-Driven Regeneration Flow

When a rejected item is regenerated:

```mermaid
sequenceDiagram
    autonumber
    actor Reviewer as Human Reviewer
    participant UI as Streamlit Dashboard
    participant API as FastAPI Backend
    participant DB as SQLite
    participant FA as Feedback Agent
    participant CA as Content Agent
    participant COMP as Compliance Agent

    Reviewer->>UI: Click "↻ Regenerate"
    UI->>API: POST /content/{id}/regenerate {additional_instruction}
    
    API->>DB: get_content_by_id(parent_id)
    DB-->>API: Parent Item (retains original topic, brand, platform)
    
    API->>FA: get_recent_feedback(brand, n=5)
    FA-->>API: [Latest rejection note + historical corrections]
    
    API->>CA: generate(topic=parent.topic, feedback=recent_feedback, additional_instruction)
    CA-->>API: Compliant regenerated copy (avoids previous error)
    
    API->>COMP: check(regenerated_content, brand)
    COMP-->>API: {status: "pass", reasons: []}
    
    API->>DB: insert_content(status="pending", parent_id=parent.id, cycle=parent.cycle+1)
    DB-->>API: New Variant Item (#NewID)
    API-->>UI: Return New Variant
    UI-->>Reviewer: Display side-by-side Before/After diff and PASS badge
```

---

## 4. Centralized Analytics & Real Metric Derivation

Every metric displayed on the dashboard is computed directly from SQLite records:

| Metric | SQL / Computation Formula | Empty DB Behavior |
|---|---|---|
| `pending_count` | `SELECT COUNT(*) FROM content_queue WHERE status = 'pending'` | `0` |
| `approved_count` | `SELECT COUNT(*) FROM content_queue WHERE status = 'approved'` | `0` |
| `rejected_count` | `SELECT COUNT(*) FROM content_queue WHERE status = 'rejected'` | `0` |
| `scheduled_count` | `SELECT COUNT(*) FROM content_queue WHERE status = 'scheduled'` | `0` |
| `total_assets` | `SELECT COUNT(*) FROM content_queue` | `0` |
| `total_feedback` | `SELECT COUNT(*) FROM feedback` | `0` |
| `overall_rejection_rate` | `(rejected_count / total_reviewed) * 100` | `0.0%` |
| `latest_cycle` | `SELECT MAX(cycle) FROM content_queue` | `None` / `0` |
| `latest_cycle_rejection_rate` | Rejection rate of `MAX(cycle)` | `0.0%` ("No data") |
| `relative_error_reduction` | `((c1_rate - latest_rate) / c1_rate) * 100` if `cycles >= 2` and `c1_rate > 0` | `"N/A"` |
| `knowledge_source_count` | `len(load_all_sources())` | `5` |
| `lead_count` | `SELECT COUNT(*) FROM leads` | `0` |

---

## 5. Lead Agent Scoring Criteria Pipeline

The Lead Agent evaluates potential prospects using five explicit, normalized dimensions:

```mermaid
graph LR
    Input([Lead Request: Vertical, Region, Query]) --> LA[Lead Agent]
    LA --> S1[1. Vertical Alignment Score: 0-25 pts]
    LA --> S2[2. Regional Jurisdiction Score: 0-20 pts]
    LA --> S3[3. Business Risk Profile Score: 0-20 pts]
    LA --> S4[4. InsurTech Relevance Score: 0-20 pts]
    LA --> S5[5. Public Information Verifiability: 0-15 pts]
    S1 & S2 & S3 & S4 & S5 --> Total[Total Fit Score: 0-100]
    Total --> Draft[Generate Bespoke Compliant Outreach Draft]
    Draft --> Output[(Save Lead with Source Attribution)]
```

- **Rule:** If live research yields no verifiable public listings, no fabricated contact is generated.
