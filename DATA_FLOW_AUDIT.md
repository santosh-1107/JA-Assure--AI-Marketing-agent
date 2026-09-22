# System-Wide Data Flow Audit & Provenance Verification

**System:** JA Assure AI Marketing Intelligence & Risk Agent  
**Jurisdiction / Scope:** Regulated InsurTech Content Generation, Factual Grounding, Governance & Risk Gating  
**Audit Date:** 2026-09-22  
**Audited Components:** End-to-End Pipeline from User Request to Dashboard Analytics

---

## 1. System Pipeline Overview

```
User Request (Topic, Brand, Product, Platform)
    │
    ▼
Research Agent (Tier 1 JA Assure RAG + Tier 3 Competitor Intelligence)
    │
    ▼
Knowledge Retriever (PDF Chunks via ChromaDB 'company_knowledge')
    │
    ▼
Competitor Research Agent (Public Market Profiles / Live Tavily)
    │
    ▼
Context Builder (XML Boundary Tags + Injection Defense Header)
    │
    ▼
Content Agent (Pre-generation Brand Knowledge Validation)
    │
    ▼
Groq Provider / LLM Service (Structured JSON Generation + 1-Retry Repair)
    │
    ▼
Generated Content Asset (Draft Copy + Claims Used Metadata)
    │
    ▼
Claim Grounding Layer (Extraction & Semantic Mapping against Authoritative Context)
    │
    ▼
Risk / Compliance Agent (Stage 2 Gate: YAML Rubric Evaluation + Grounding Evaluation)
    │
    ▼
Content Queue Storage (SQLite `content_queue`, status='pending')
    │
    ▼
Human Review Governance (Approve, Reject, or Edit with State Machine Enforcement)
    │
    ▼
Feedback Agent (SQLite `feedback` table + Structured Reviewer Annotations)
    │
    ▼
Vector Store Embeddings (ChromaDB `feedback_embeddings` collection)
    │
    ▼
Semantic Feedback Retrieval (Query-similar historical corrections retrieved)
    │
    ▼
Future Generation (Few-shot negative constraints & qualifications injected)
    │
    ▼
Dashboard Analytics (Direct SQLite aggregations for review counts, rates, trends, and heatmaps)
```

---

## 2. Transition-by-Transition Data Flow Specifications

### Transition 1: User Request → Research Agent
* **Input:**
  * `brand`: `"Jade"` or `"DoctorShield"` (`BrandLiteral`)
  * `product`: e.g., `"Jewellers Block & Specie"` or `"Medical Malpractice Indemnity"`
  * `topic`: Free-text topic string (min length 3)
  * `platform`: `"LinkedIn"`, `"Instagram"`, or `"X"` (`PlatformLiteral`)
  * `competitor_list`: Optional list of competitor names
* **Output:**
  * `matched_sources`: Top-k authoritative PDF chunks
  * `competitor_profiles`: Extracted competitor posture profiles
  * `summary`, `recommendation`, `web_research_status`, `is_live_search`
* **Data Source:** User input payload via REST endpoint `/content/research` or Content Studio UI.
* **Transformation:** Tokenization of topic, query vector construction, competitor list normalization.
* **Database / Table:** Reads from ChromaDB collection `company_knowledge`.
* **Validation:** Pydantic `ResearchRequest` schema validation; brand enum checking (`Jade`, `DoctorShield`).
* **Error Handling:** Fallback to canonical seed resources if vector query encounters missing collection.
* **Source Metadata:** `id`, `filename`, `page_number`, `section`, `tier="TIER_1_AUTHORITATIVE"`.
* **Real or Hardcoded:** **REAL** — Dynamically derived from ChromaDB vector search and query tokens.

---

### Transition 2: Research Agent → Knowledge Retriever (RAG)
* **Input:** `brand`, `topic`, `product`, `top_k=2`
* **Output:** List of `SourceItem` dictionaries containing chunk text, exact page numbers, section headers, and similarity scores.
* **Data Source:** Official JA Assure PDFs located in `data/knowledge/pdfs/`:
  * `JA_Assure_Jewellers_Block_Guide.pdf` (Jade)
  * `JA_Assure_DoctorShield_Medical_Malpractice_Guide.pdf` (DoctorShield)
  * `JA_Assure_Corporate_Architecture.pdf` (Corporate general)
* **Transformation:** Fast deterministic dense vector generation (L2-normalized 256-dim embeddings) + token BM25 overlap score calculation:
  $$\text{Score} = 0.65 \times \text{VectorSim} + 0.20 \times \text{TokenOverlap} + 0.15 \times \text{BrandBoost}$$
* **Database / Table:** ChromaDB `company_knowledge` collection.
* **Validation:** Verification that PDF exists, contains non-empty text, and is 1-indexed by page.
* **Error Handling:** If ChromaDB has 0 records, automatically triggers `pdf_pipeline.ingest_all_pdfs()`; fallback to verified resource JSONs.
* **Source Metadata:** Exact PDF basename (e.g. `JA_Assure_Jewellers_Block_Guide.pdf`), `page_number` (e.g. `3`), `section`.
* **Real or Hardcoded:** **REAL** — Chunks parsed page-by-page from physical PDF documents via `pypdf`.

---

### Transition 3: Research Agent → Competitor Intelligence
* **Input:** `competitor` name, `industry`, `region`, `product_category`
* **Output:** Structured dictionary with `messaging`, `claims`, `cta`, `tone`, `themes`, `positioning`, `source`, `web_research_status`, `is_live_search`.
* **Data Source:**
  * **When `TAVILY_API_KEY` configured:** Live Tavily Search API (`https://api.tavily.com/search`).
  * **When `TAVILY_API_KEY` empty / unconfigured:** Verified local InsurTech market profiles for commercial property vs specialty carriers.
* **Transformation:** Extraction of marketing CTAs, tone, and theme keywords; explicit labeling as `TIER_3_EXTERNAL_INTELLIGENCE`.
* **Database / Table:** Ephemeral memory; passed downstream in `generation_metadata`.
* **Validation:** Check for API key presence and HTTP status 200.
* **Error Handling:** Wrapped in `try...except httpx.HTTPError`; falls back to local market profiles and sets `web_research_status = "EXTERNAL RESEARCH UNAVAILABLE (OFFLINE MODE)"`.
* **Source Metadata:** Real external URL if live search; `"OFFLINE / LOCAL MARKET PROFILE (Web Search Unavailable)"` if offline.
* **Real or Hardcoded:** **REAL DYNAMIC PROFILE** when offline; **LIVE WEB DATA** when Tavily configured. Clearly labels offline status.

---

### Transition 4: Knowledge Layer → Context Builder & Guardrails
* **Input:**
  * Source A: Authoritative PDF sources (Tier 1)
  * Source B: Compliance rubric rules (Tier 2)
  * Source C: Historical reviewer feedback (Tier 2/Guidance)
  * Source D: Competitor intelligence (Tier 3)
  * User request: Brand, product, platform, topic
* **Output:** Full LLM user prompt with strict XML boundary encapsulation and prompt injection defense headers.
* **Data Source:** In-memory outputs from Transitions 1, 2, and 3.
* **Transformation:** Encapsulates content into `<AUTHORITATIVE_KNOWLEDGE>`, `<COMPLIANCE_RULES>`, `<HISTORICAL_FEEDBACK>`, `<COMPETITOR_INTELLIGENCE>`, `<USER_REQUEST>`.
* **Database / Table:** None (Prompt assembly).
* **Validation:** `validate_brand_knowledge_match` verifies that requested brand and product match the retrieved knowledge. Returns `(False, "Insufficient authoritative knowledge for this product request.")` on mismatch.
* **Error Handling:** If mismatch detected, generation terminates before calling LLM and returns structured failure.
* **Source Metadata:** Source IDs and page numbers formatted inside XML tags.
* **Real or Hardcoded:** **REAL** — Dynamically constructed per request.

---

### Transition 5: Context Builder → Content Agent & LLM Service
* **Input:** System prompt (`MANDATED_SYSTEM_PROMPT` + brand persona + output schema) + Structured User Prompt.
* **Output:** Raw LLM response string (expected structured JSON).
* **Data Source:** Groq API (`llama-3.3-70b-versatile` or configured fallback models) or Gemini API (`gemini-2.5-flash`).
* **Transformation:** Inference via HTTP client with `response_format={"type": "json_object"}`.
* **Database / Table:** None.
* **Validation:** `validate_and_parse_groq_output` validates required JSON keys: `content`, `brand`, `product`, `platform`, `topic`, `claims_used`, `uncertain_claims`, `feedback_applied`, `generation_status`.
* **Error Handling:**
  1. If JSON is malformed or missing keys, executes **1-retry repair** via `repair_groq_output`.
  2. If repair fails, attempts Gemini fallback.
  3. If both providers fail, raises `LLMGenerationError`. Never falls back silently to hardcoded copy.
* **Source Metadata:** Model name, provider name, latency timestamp.
* **Real or Hardcoded:** **REAL LIVE INFERENCE** via Groq Cloud API.

---

### Transition 6: Generated Content → Claim Grounding Layer
* **Input:** Generated text `content` + `claims_used` reported by LLM + `authoritative_sources` from RAG.
* **Output:** List of evaluated claims with grounding status: `SUPPORTED`, `UNSUPPORTED`, or `UNCERTAIN`.
* **Data Source:** Output of Transition 5 + authoritative sources from Transition 2.
* **Transformation:**
  1. `extract_claims`: Sentence splitting, filtering out non-claim headers (ending with `:`) and short phrases (< 4 words), keyword extraction.
  2. `verify_grounding`: Prohibited pattern check (e.g. `100% protection`, `guaranteed payout`, fabricated numbers not in text); safe generic wording check; entity overlap against authoritative PDF chunks.
* **Database / Table:** Ephemeral memory; stored in SQLite `content_queue.generation_metadata`.
* **Validation:** Claims must be grounded in retrieved PDF context or safe generic phrases. Fabricated coverage limits (e.g. `$500,000,000`) flagged as `UNSUPPORTED`.
* **Error Handling:** If no sources exist, all factual claims marked `UNSUPPORTED` or `UNCERTAIN`.
* **Source Metadata:** `source_id`, `page`, `reason`.
* **Real or Hardcoded:** **REAL ALGORITHMIC VERIFICATION** — No hardcoded verdicts.

---

### Transition 7: Claim Grounding → Risk / Compliance Agent
* **Input:** `content`, `brand`, `claim_grounding` evaluations.
* **Output:** `ComplianceResult` containing:
  * `status`: `"pass"` or `"fail"`
  * `risk_score`: `0.0` to `100.0` (calculated from issue severity weights)
  * `risk_level`: `"LOW"`, `"MEDIUM"`, or `"HIGH"`
  * `issues`: Structured list with `rule_id`, `severity`, `evidence`, `explanation`
  * `reasons`: Triggered compliance reasons
* **Data Source:** External YAML rubrics (`rubrics/jade.yaml` and `rubrics/doctorshield.yaml`).
* **Transformation:**
  1. Text normalization via `normalize_compliance_text` (lowercasing, unicode dashes `\u2010-\u2015`, punctuation stripping).
  2. Deterministic regex and word-boundary matching across rubric trigger patterns.
  3. Mandatory disclosure phrase check (e.g. `"subject to policy terms and conditions"`).
  4. Integration of Stage 1 Claim Grounding: `UNSUPPORTED` claims trigger `UNSUPPORTED_FACTUAL_CLAIM` (`CRITICAL` severity, +45 points).
* **Database / Table:** None (In-memory rule engine).
* **Validation:** Only valid rule IDs from the YAML rubric or `UNSUPPORTED_FACTUAL_CLAIM` are permitted.
* **Error Handling:** Missing rubric files raise `FileNotFoundError`; unknown brands raise `ValueError`.
* **Source Metadata:** YAML rule reference (e.g. `"General Insurance Advertising Standards — Prohibition on Guaranteed Outcomes"`).
* **Real or Hardcoded:** **REAL** — Risk score calculated dynamically based on detected issues:
  $$\text{RiskScore} = \min(100.0, \sum \text{SeverityWeights})$$

---

### Transition 8: Risk Result → SQLite Database (`content_queue`)
* **Input:** Content copy, brand, platform, topic, product, cycle, compliance verdict, source citations, generation metadata.
* **Output:** Database record ID (`int`), status initialized to `'pending'`.
* **Data Source:** Combined output from Transitions 5, 6, and 7.
* **Transformation:** Serialization to SQLite types (JSON strings for `compliance_result`, `sources`, `generation_metadata`).
* **Database / Table:** SQLite `content_queue` table.
* **Validation:** NOT NULL constraints on `brand`, `platform`, `content_type`, `content`, `status`.
* **Error Handling:** Database transaction rolled back on constraint violation.
* **Source Metadata:** `prompt_version`, `knowledge_source_ids`, `model`, `generation_mode`.
* **Real or Hardcoded:** **REAL DATABASE ROW** inserted via parameterized SQL.

---

### Transition 9: SQLite (`content_queue`) → Human Review UI
* **Input:** `content_id` or query parameter `brand`.
* **Output:** Review queue cards rendered in Streamlit UI.
* **Data Source:** SQLite query `SELECT * FROM content_queue WHERE status = 'pending' ORDER BY created_at DESC`.
* **Transformation:** Deserialization of JSON fields into UI cards, risk badges, claim grounding summary, and source citations.
* **Database / Table:** SQLite `content_queue`.
* **Validation:** Verification that asset is in `pending` state.
* **Error Handling:** Graceful empty state when no items await review.
* **Source Metadata:** Display of exact PDF name and page number for human verification.
* **Real or Hardcoded:** **REAL** — Queried from database on every page render.

---

### Transition 10: Human Review Action → State Machine & Feedback Storage
* **Input:**
  * **Approve:** `content_id`
  * **Reject:** `content_id`, `tag`, `note` (free-text reviewer note)
  * **Edit:** `content_id`, `edited_content`, optional `tag`, `note`
* **Output:** Updated `content_queue` record; new record in `feedback` table.
* **Data Source:** Human reviewer inputs via UI buttons and text areas.
* **Transformation:**
  * If **Approve**: Validates `status == 'pending'` AND `compliance_result.status == 'pass'`. Updates `status = 'approved'`.
  * If **Reject**: Validates `status == 'pending'`, `tag in VALID_TAGS`, `note != ''`. Updates `status = 'rejected'`. Inserts into `feedback`.
  * If **Edit**: Resets `status = 'pending'`, re-runs compliance check on edited copy, updates `content`.
* **Database / Table:** SQLite `content_queue` and `feedback` tables.
* **Validation:** Strict state machine enforcement:
  * `FAILED -> APPROVED`: **BLOCKED** with `Compliance Governance Violation`.
  * `REJECTED -> APPROVED`: **BLOCKED** with `State Machine Violation`.
  * `EDITED -> APPROVED`: **BLOCKED** until compliance check passes.
* **Error Handling:** Raises `ValueError` caught and returned as HTTP 400.
* **Source Metadata:** Reviewer timestamp `CURRENT_TIMESTAMP`, original content, corrected content.
* **Real or Hardcoded:** **REAL** — User input written to persistent SQLite tables.

---

### Transition 11: Feedback Storage → Vector Store (`feedback_embeddings`)
* **Input:** `feedback_id`, `content_id`, `original_content`, `reviewer_note`, `tag`, `brand`, `product`, `platform`, `risk_score`.
* **Output:** Vector embedding ID (e.g. `fb-12`).
* **Data Source:** SQLite `feedback` row inserted in Transition 10.
* **Transformation:**
  * Assembles dense semantic document:
    `Brand: {brand} | Platform: {platform} | Issue: {tag} | Original Flawed: {original} | Reviewer Note: {note}`
  * Computes 256-dim dense vector using word features, domain weights, and sub-word n-grams.
* **Database / Table:** ChromaDB `feedback_embeddings` collection.
* **Validation:** Verifies collection isolation (separate from `company_knowledge`).
* **Error Handling:** Wrapped in `try...except` to prevent non-fatal vector lock in concurrent tests.
* **Source Metadata:** `feedback_id`, `content_id`, `brand`, `rejection_tag`, `risk_score`.
* **Real or Hardcoded:** **REAL EMBEDDING** stored in local ChromaDB vector index.

---

### Transition 12: Future Generation → Semantic Feedback Retrieval
* **Input:** `clean_topic`, `brand`, `product`, `platform`, `top_k=4`.
* **Output:** List of top semantically matching historical corrections.
* **Data Source:** ChromaDB `feedback_embeddings` collection supplemented by SQLite `feedback` table.
* **Transformation:** Vector similarity search with cosine distance:
  $$\text{Similarity} = \frac{1.0}{1.0 + \text{Distance}}$$
* **Database / Table:** ChromaDB `feedback_embeddings` + SQLite `feedback`.
* **Validation:** Results filtered by brand and sorted descending by similarity score.
* **Error Handling:** If vector store is empty, gracefully falls back to recent SQLite feedback rows.
* **Source Metadata:** `feedback_id`, `reviewer_note`, `issue_type`, `similarity_score`.
* **Real or Hardcoded:** **REAL SEMANTIC RETRIEVAL** — Matches semantic intent even when verbatim phrasing differs.

---

### Transition 13: Database Records → Dashboard Analytics & Heatmap
* **Input:** `db_path`
* **Output:** Operational KPIs, cycle rejection rates, relative error reduction, issue breakdown, risk heatmap matrix.
* **Data Source:** SQLite tables: `content_queue`, `feedback`, `leads`.
* **Transformation:** SQL aggregations:
  * `COUNT(*)`, `SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END)`
  * Group-by cycle rejection rate:
    $$\text{RejectionRate}_{\text{cycle}} = \frac{\text{Rejected}}{\text{Total Reviewed}} \times 100$$
  * Heatmap 2D cross-tabulation: Matrix of issue types vs brands/platforms.
* **Database / Table:** SQLite `content_queue`, `feedback`, `leads`.
* **Validation:** Divisor checked for zero before division; returns `0.0` or `None` if no data exists.
* **Error Handling:** SQLite connection safely closed in `finally` blocks.
* **Source Metadata:** Schema columns, counts, real timestamps.
* **Real or Hardcoded:** **REAL** — 100% database-driven. Zero hardcoded KPIs or dummy trends.

---

## 3. Data Provenance Summary Matrix

| Metric / Asset | Origin Source | Query / Extraction Mechanism | Storage Location | Real or Hardcoded |
| :--- | :--- | :--- | :--- | :--- |
| **Product Specs & Limits** | Official JA Assure PDFs | `pypdf` extraction, page-level chunking | ChromaDB `company_knowledge` | **REAL** |
| **Compliance Rules** | Official YAML Rubrics | PyYAML loader, normalized regex matching | `rubrics/*.yaml` | **REAL** |
| **Competitor Analysis** | Public Market Research | Live Tavily API or structured market profiles | Ephemeral context | **REAL / LABELED OFFLINE** |
| **Generated Marketing Copy** | Groq Cloud LLM | `GroqProvider.generate` with JSON schema | SQLite `content_queue.content` | **REAL** |
| **Claim Grounding Verdicts** | Grounding Verifier | Token overlap & prohibited pattern check | SQLite `content_queue.generation_metadata` | **REAL** |
| **Risk Score & Reasons** | Risk / Compliance Agent | Rule severity summation | SQLite `content_queue.compliance_result` | **REAL** |
| **Reviewer Corrections** | Human Reviewer | Web form submission in Streamlit | SQLite `feedback` table | **REAL** |
| **Feedback Vectors** | Fast Local Embedding | Dense 256-dim L2 normalized embedding | ChromaDB `feedback_embeddings` | **REAL** |
| **Dashboard Metrics** | Database Aggregations | `SELECT COUNT(*), SUM(...) FROM ...` | Derived dynamically | **REAL** |
| **Risk Heatmap** | Database Aggregations | `GROUP BY issue, brand/platform` | Derived dynamically | **REAL** |

---
*Audit Completed and Verified against Active Codebase.*
