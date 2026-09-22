# JA Assure AI Marketing Intelligence & Risk Agent — System Walkthrough

## Overview

The **JA Assure AI Marketing Intelligence & Risk Agent** is an enterprise-grade agentic marketing and regulatory risk governance system engineered for regulated InsurTech Managing General Agents (MGAs). The platform safeguards two specialized JA Assure insurance brands:

- **Jade**: High-value asset, luxury jewellery, fine art, and commercial Jewellers Block & Specie insurance.
- **DoctorShield**: Healthcare professional indemnity, medical malpractice litigation defense financing, and statutory council (SMC/MMC) inquiry representation.

The system ensures that all generated marketing copy is strictly grounded in authoritative company knowledge, evaluated against regulatory advertising rubrics, signed off by human reviewers, and continuously refined via semantic feedback memory.

---

## Complete Data Flow & Pipeline Walkthrough

```
User Request (Topic, Brand, Product, Platform)
       │
       ▼
Research Agent (Hybrid RAG Search on Official PDFs + Tier 3 Competitor Context)
       │
       ▼
Content Agent (Brand Voice Configuration + Negative Feedback Directives)
       │
       ▼
Prompt Injection Defense (Strict XML Containerization: Passive Data Tagging)
       │
       ▼
Groq LLM Engine (openai/gpt-oss-20b with Gemini 2.5 Flash Fallback)
       │
       ▼
Structured Output Validation & 1-Retry Repair
       │
       ▼
Claim Grounding Verification (Extracts & Validates Factual Claims against PDFs)
       │
       ▼
Compliance / Risk Agent (Stage 2 Regulatory Rubric Check: PASS / FAIL)
       │
       ▼
SQLite Database (`content_queue`, status='pending')
       │
       ▼
Streamlit Review Workspace (Human-in-the-Loop Governance: Approve, Reject, or Edit)
       │
   ┌───┴────────────────────────┐
   ▼                            ▼
Approved Content            Rejected / Edited Content
(Scheduled for Publishing)   (Tag + Reviewer Note Recorded)
                                │
                                ▼
                            ChromaDB Semantic Feedback Embedding
                                │
                                ▼
                            Injected into Future Generation Prompts
```

---

## Key Features & Verified Capabilities

### 1. Topic-Aware Generation & Authoritative RAG Grounding
- **Mandatory Topic Enforcement:** Rejects empty, whitespace-only, or missing topics with HTTP 422 / ValueError.
- **Dynamic Retrieval:** `KnowledgeRetriever` performs hybrid vector + keyword retrieval on page-attributed chunks from official JA Assure guide PDFs.
- **Domain Guardrails:** Out-of-domain requests return a clear `"Insufficient authoritative knowledge for this product request"` message instead of silently injecting unrelated jewellery or medical facts.
- **Zero Static Demo Copy:** All marketing content is assembled dynamically using verified brand voice prompts and authoritative facts.

### 2. Live LLM Integration with Multi-Provider Failover
- **Primary Live LLM:** Groq API (`openai/gpt-oss-20b`, `qwen/qwen3.8-27b`, `openai/gpt-oss-120b`, `llama-3.3-70b-versatile`).
- **Secondary Failover:** Google Gemini API (`gemini-2.5-flash` via `google-genai` SDK).
- **Offline Generator:** Dynamic rule-grounded generator ensuring 100% offline resilience and testing safety.
- **Structured Schema & Repair:** Validates JSON output schema and executes automatic 1-retry repair on malformed responses.

### 3. Human Edit Persistence & Compliance Invalidation
- **Database Persistence:** Reviewer edits are saved directly to SQLite `content_queue` under the asset's `content_id`.
- **Compliance Invalidation:** Editing content immediately invalidates previous compliance results and triggers a fresh evaluation.
- **Approval Blocking:** If edited content violates compliance rules (e.g. introduces "100% protection" or "guaranteed payout"), status remains `pending` and approval is strictly blocked (HTTP 400).
- **Audit History:** Full edit history, original copy, reviewer notes, and version progression are preserved in `generation_metadata`.

### 4. Closed-Loop Semantic Feedback Learning
- **Reviewer Feedback Capture:** Rejections and edits record structured tags (`inaccurate_claim`, `unsupported_guarantee`, `too_salesy`, `off_brand_tone`, `missing_qualifier`, `human_edit`) and notes.
- **Semantic Vector Storage:** Feedback is indexed into ChromaDB's `feedback_embeddings` collection.
- **Pre-Generation Retrieval:** Semantic search queries past mistakes relevant to the requested topic and injects them as negative few-shot constraints.
- **Visible Improvement:** In demonstration audit scenarios, regeneration incorporating reviewer feedback successfully resolves flaws and passes compliance.

### 5. Multi-Criteria Lead Generation
- **5-Dimension Fit Scoring:** Evaluates prospective business leads across vertical alignment (25%), geographic jurisdiction (20%), business risk profile (20%), indemnity relevance (20%), and public information quality (15%).
- **Personalized Outreach:** Automatically drafts tailored, compliant B2B outreach messaging referencing verified risk management priorities.
- **Contact Integrity:** Zero synthetic or fabricated personal email addresses; live queries require public verification.

### 6. Real-Time Database Analytics & Risk Heatmap
- **Database-Driven Metrics:** Real-time calculation of total assets, pending queue, approved count, rejected count, rejection rates, and cycle progressions.
- **Risk Heatmap Matrix:** Visual matrix grouping regulatory issues across brands and platforms dynamically from SQLite review records.
- **No Static Stats:** Eliminates fake hardcoded improvement percentages.

---

## Verification & Test Results

The entire codebase is validated by an automated test suite across 11 test modules:

```bash
pytest tests/ -v
```

### Module Summary:
1. `tests/test_api.py` (5 tests): FastAPI REST routes, health checks, generation, approval, rejection, and leads.
2. `tests/test_audit_fixes.py` (27 tests): Schema migrations, database isolation, dynamic analytics, topic preservation, and rubric references.
3. `tests/test_compliance.py` (7 tests): Jade and DoctorShield compliance rubrics, pattern matching, and normalization.
4. `tests/test_content_generation_topics.py` (9 tests): Topic validation, prompt construction, distinct topic copy, and variant diversity.
5. `tests/test_database.py` (6 tests): SQLite CRUD, human review state transitions, and rejection rate calculations.
6. `tests/test_end_to_end_audit_scenario.py` (1 test): Complete 21-step data provenance and feedback loop scenario.
7. `tests/test_feedback_loop.py` (7 tests): 10-step reviewer rejection, vector indexing, and compliant regeneration.
8. `tests/test_groq_guardrails.py` (12 tests): System prompt mandates, XML prompt isolation, schema validation, repair retries, and claim grounding.
9. `tests/test_hallucination_suite.py` (12 tests): Anti-hallucination bounds, injection defense, and brand/product isolation.
10. `tests/test_human_edit_persistence.py` (8 tests): Human edit persistence, database reloads, compliance re-evaluations, and approval gates.
11. `tests/test_rag_and_risk_intelligence.py` (8 tests): PDF ingestion, hybrid vector retrieval, and risk heatmap analytics.

---

## Configuration & Environment Setup

Configure application environment in `.env`:

```ini
# LLM Providers
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-20b
GEMINI_API_KEY=your_gemini_api_key_here
LLM_PROVIDER=groq

# Optional Research & Multimodal Providers
TAVILY_API_KEY=your_tavily_api_key_here
IMAGE_PROVIDER=offline

# Runtime Environment
DEMO_MODE=false
JA_ASSURE_DB_PATH=data/ja_assure.db
```

### Running the Application:
- **Backend API:** `uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload`
- **Dashboard UI:** `streamlit run dashboard/app.py`
