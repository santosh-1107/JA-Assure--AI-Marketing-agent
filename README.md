# JA Assure AI Marketing Intelligence & Risk Agent

## Problem Statement

Insurance marketing is high-risk. Generic AI can generate attractive marketing content without understanding an insurer's actual product knowledge, marketing restrictions, brand voice, previous reviewer corrections, and market context. In regulated insurance jurisdictions, generating ungrounded claims, absolute guarantees (such as "100% payout guaranteed"), or misleading coverage promises creates immediate regulatory liability, severe financial sanctions, and reputational damage.

## Solution

JA Assure AI Marketing Intelligence & Risk Agent is an organisation-aware AI marketing and regulatory risk management system that:

- retrieves authoritative JA Assure knowledge using RAG
- researches market and competitor information
- generates brand-specific and platform-specific marketing content
- detects unsupported or risky claims
- requires human approval
- learns from reviewer feedback
- generates multiple marketing formats
- supports image generation where configured
- provides analytics and risk intelligence

---

## Architecture

```
User / Reviewer Request
         ↓
Research / Knowledge Retrieval (Tier 1 PDFs + Tier 3 Market Context)
         ↓
   Content Agent (Brand Voice YAML + Platform Guidelines)
         ↓
   RAG Grounding (Authoritative Source Verification)
         ↓
  Groq LLM Engine (openai/gpt-oss-20b / Gemini 2.5 Flash Fallback)
         ↓
Risk / Compliance Agent (Brand Rubrics + Claim Grounding Gate)
         ↓
   Human Review (Interactive Streamlit Workspace)
         ↓
  Approved / Rejected / Edited
         ↓
  Feedback Memory (SQLite Audit Trail)
         ↓
  Semantic Retrieval (ChromaDB Vector Store)
         ↓
  Future Generation (Few-Shot Negative Constraints)
```

---

## Agents

### 1. Content Agent (`backend/agents/content_agent.py`)
- **Purpose:** Generates brand-aligned, topic-specific marketing copy strictly grounded in authoritative company knowledge.
- **Input:** `topic` (mandatory string), `brand` ("Jade" | "DoctorShield"), `product`, `platform` ("LinkedIn" | "Instagram" | "X"), `content_type` ("post" | "carousel" | "tweet" | "video_script"), optional `rag_context`, `past_corrections`, `additional_instruction`, `num_variants`.
- **Processing:** Validates parameters; queries Research Agent for authoritative sources; matches brand-product boundaries; retrieves semantic feedback; constructs 4-tier prompt with strict XML boundary tags; invokes `LLMService` (Groq primary, Gemini fallback, offline dynamic generator resilience); extracts factual claims and verifies grounding.
- **Output:** Structured payload containing `content`, `brand`, `product`, `platform`, `topic`, `variant_id`, `provider`, `generation_mode`, `model`, `prompt_version`, `knowledge_source_ids`, `feedback_ids`, `claim_grounding`, and `variants`.
- **Data Sources:** Brand guidelines (`prompts/jade.yaml`, `prompts/doctorshield.yaml`), Tier 1 PDF knowledge chunks via RAG, ChromaDB feedback embeddings.
- **Limitations:** Dependent on available authoritative documents; will refuse generation with "Insufficient authoritative knowledge for this product request" if requested topic or brand does not match verified knowledge.

### 2. Research Agent (`backend/agents/research_agent.py`)
- **Purpose:** Aggregates authoritative JA Assure product knowledge and contextual competitor intelligence.
- **Input:** `brand`, `topic`, optional `product`, `competitor_list`.
- **Processing:** Invokes `KnowledgeRetriever` for local PDF hybrid vector/keyword search; runs competitor contrast research using Tavily Search API if configured, or falls back to verified offline competitor positioning profiles.
- **Output:** Comprehensive research dossier containing `sources` (page-attributed citations), `competitor_analysis` (messaging, tone, contrast positioning), `summary`, `recommendation`, and `web_research_status`.
- **Data Sources:** `data/knowledge/pdfs/` via ChromaDB, official product briefs, optional Tavily Web Search API.
- **Limitations:** Live competitor research requires a valid `TAVILY_API_KEY`. In the absence of an API key, operates strictly in verified offline/local mode.

### 3. Risk / Compliance Agent (`backend/agents/compliance_agent.py`)
- **Purpose:** Evaluates marketing content against regulatory insurance rubrics and verifies factual claim grounding.
- **Input:** `content`, `brand`, optional `claim_grounding` evals.
- **Processing:** Normalizes copy (whitespace, hyphens, punctuation); executes deterministic regex checks against prohibited patterns; validates required policy qualification phrases (e.g., "subject to policy terms and conditions"); evaluates ungrounded/uncertain claims from claim verifier; calculates continuous risk score (0–100) and assigns risk tier (`LOW`, `MEDIUM`, `HIGH`).
- **Output:** `ComplianceResult` dict with `status` ("pass" | "fail"), `risk_score` (float), `risk_level` ("LOW" | "MEDIUM" | "HIGH"), and structured `issues` list (`rule_id`, `issue_type`, `severity`, `evidence`, `explanation`, `reference`).
- **Data Sources:** External regulatory YAML rubrics (`rubrics/jade.yaml`, `rubrics/doctorshield.yaml`), post-generation claim grounding verifications.
- **Limitations:** Deterministic matching covers documented patterns; novel semantic edge cases can be augmented with LLM verification when Gemini API is active.

### 4. Feedback Agent (`backend/agents/feedback_agent.py`)
- **Purpose:** Captures human reviewer edits and rejections, storing structured feedback and enabling semantic retrieval for few-shot prompt injection.
- **Input:** Reviewer rejections (`tag`, `note`, `issue_type`, `flawed_content`) or edits (`edited_content`, `original_content`).
- **Processing:** Records feedback in SQLite `feedback` table; indexes vector embeddings into ChromaDB `feedback_embeddings` collection; computes semantic query similarity to retrieve relevant historical corrections for new generation prompts.
- **Output:** List of relevant historical corrections formatted with negative constraints (`format_feedback_for_prompt`).
- **Data Sources:** SQLite `feedback` table, ChromaDB `feedback_embeddings` collection.
- **Limitations:** Retrieval quality depends on similarity between incoming topic and previously recorded review feedback notes.

### 5. Lead Agent (`backend/agents/lead_agent.py`)
- **Purpose:** Identifies, enriches, and scores prospective commercial accounts and clinical practices for personalized outreach.
- **Input:** `vertical` ("Clinics" | "Hospitals" | "Jewellers" | "Bullion"), `region`, `search_terms`.
- **Processing:** Gathers prospect profiles; computes objective 5-criteria fit score (vertical match, geographic alignment, business profile, insurance risk relevance, public info quality); drafts personalized, compliance-aligned outreach copy.
- **Output:** List of scored prospects with `name`, `contact`, `vertical`, `fit_score` (0–100), `outreach_draft`, and status.
- **Data Sources:** Verified public business registries and healthcare directory templates.
- **Limitations:** Live prospecting requires external web integration; offline demo profiles are explicitly labeled to prevent contact fabrication.

---

## RAG Knowledge Layer

```
Official JA Assure PDFs
        ↓
Text & Page Extraction (`pdfplumber` / `pypdf`)
        ↓
Metadata Tagging (`filename`, `page_number`, `section`, `brand`, `product`)
        ↓
Chunking (500 characters with 100-character overlap)
        ↓
Embeddings (`FastLocalEmbeddingFunction` - 256-dimensional semantic hash)
        ↓
ChromaDB Persistent Storage (`data/chromadb/company_knowledge`)
        ↓
Semantic + Keyword Hybrid Retrieval
        ↓
Grounded Generation & Source Attribution
```

**CRITICAL PRINCIPLE:** Authoritative JA Assure company information comes strictly from the knowledge layer. The LLM is treated solely as a natural-language composition engine and is **never** treated as a source of truth for coverage terms, policy exclusions, or insurance facts.

---

## Content Generation

### Brand Voices
- **Jade**: Luxury private client advisory tone. Emphasizes generational wealth preservation, bespoke bullion/jewellery safeguarding, dual-custody vault protocols, and Lloyd's coverholder underwriting criteria. Strictly prohibits discount slang ("cheap", "flash sale") and clinical jargon.
- **DoctorShield**: Dignified, clinical, peer-to-peer advisory tone. Focuses on medico-legal defense financing, Singapore Medical Council (SMC) & Malaysian Medical Council (MMC) statutory inquiry representation, and claims-made coverage structures. Strictly prohibits guaranteed litigation dismissal or medical advice.

### Supported Platforms
- **LinkedIn**: Thought-leadership framing, executive insights, industry context, qualified call-to-action.
- **Instagram**: Visually focused copy, crisp spacing, curated hashtags.
- **X (Twitter)**: Concise single-message impact (within 280 characters).

### Multi-Variant Diversity
Supports generating multiple distinct content angles (`num_variants > 1`) across:
1. *Operational Risk & Custody Focus*
2. *Financial & Legal Governance Focus*
3. *Executive Thought-Leadership Focus*

### Model Providers & Routing
- **Primary Live Engine:** Groq API with automatic fallback sequence: `openai/gpt-oss-20b` → `qwen/qwen3.8-27b` → `openai/gpt-oss-120b` → `llama-3.3-70b-versatile`.
- **Secondary Failover Engine:** Google Gemini API (`gemini-2.5-flash` via `google-genai` SDK).
- **Offline Generator:** Dynamic rule-grounded generator assembling verified knowledge chunks when no external API is reachable.

---

## Image Generation

- **Provider:** Multimodal asset generation interface with fallback to local SVG/canvas preview rendering or external image generation API (DALL-E / Imagen / Stability).
- **Configuration:** Configured via `IMAGE_PROVIDER` in `.env`.
- **Dynamic Prompts:** Generated from brand aesthetics (Jade gold luxury palette `#D4AF37` vs DoctorShield teal clinical palette `#0D9488`), target vertical, and platform aspect ratio.
- **Storage:** Stored locally in `data/images/` or served via static URL paths.
- **Human Review & Compliance:** Images are presented alongside text copy in the Streamlit review workspace. Approving an asset covers both copy and associated visual artifacts.
- **API Setup:** If an external image provider is enabled, set the respective key (`IMAGE_API_KEY` or `OPENAI_API_KEY`) in `.env`.

---

## Compliance / Risk Intelligence

The compliance engine implements a strict two-stage risk audit:

1. **Claim Extraction:** Extracts factual assertions from marketing copy (coverage scopes, settlement promises, payout claims).
2. **RAG Grounding Verification:** Verifies each claim against authoritative Tier 1 PDF documents (`SUPPORTED`, `UNSUPPORTED`, `UNCERTAIN`).
3. **Deterministic Pattern Check:** Matches against brand-specific prohibited patterns (e.g. "guaranteed payout", "100% protected", "zero risk", "never face liability").
4. **Required Regulatory Disclosures:** Validates mandatory qualifiers (e.g., "subject to policy terms and conditions", "underwriting criteria apply").
5. **Continuous Risk Scoring:** Calculates risk score from 0.0 (fully compliant) to 100.0 (critical regulatory breach).

> [!IMPORTANT]
> **Governance Enforcements:**
> - A content item with status `fail` can **never** be approved directly. Attempting to approve a failing item returns HTTP 400.
> - An edited asset has its previous compliance verdict invalidated and **must** be re-evaluated by the Compliance Agent before any approval is permitted.

---

## Human-in-the-Loop Governance

```
       Generated Asset
              ↓
      Status: PENDING
              ↓
  Human Reviewer Inspection
    ┌─────────┼─────────┐
    ↓         ↓         ↓
 APPROVE    REJECT     EDIT
    ↓         ↓         ↓
  Status:   Status:   Status: Reset to PENDING
APPROVED  REJECTED    New Compliance Re-check
    ↓         ↓         ↓
Scheduled  Feedback  Must Pass Fresh
Publishing Recorded   Review Before
           Embedding  Approval Allowed
```

---

## Feedback Learning

- **Capture:** When a human reviewer rejects or edits content, they submit a structured tag (`inaccurate_claim`, `unsupported_guarantee`, `too_salesy`, `off_brand_tone`, `missing_qualifier`, `human_edit`) and an explicit guidance note.
- **Storage:** Recorded immutably in SQLite `feedback` table.
- **Vector Embedding:** Converted into a 256-dimensional semantic representation and indexed in ChromaDB `feedback_embeddings`.
- **Pre-Generation Retrieval:** During subsequent generation requests, `search_similar_feedback` queries the vector store for similar previous rejections.
- **Injection:** Injected into prompt as explicit negative directives: *"Under no circumstances repeat any of the rejected claims above."*
- **Mechanism:** This is **retrieval-based learning (in-context few-shot guidance)**, NOT model fine-tuning or weight updating.

---

## Competitor Intelligence

- **Default Operational Mode:** Verified offline research mode utilizing curated competitor profiles (`data/competitors.json`).
- **Live Search Integration:** Optional live web research via Tavily Search API (`TAVILY_API_KEY`).
- **Status Reporting:** API and UI explicitly report `web_research_status` as either `LIVE_WEB_SEARCH` or `EXTERNAL RESEARCH UNAVAILABLE (OFFLINE MODE)`.
- **Invariant:** Competitor intelligence is used **solely** for market positioning contrast; competitor claims are **never** treated as JA Assure facts.

---

## Lead Generation

- **Pipeline:** Industry vertical selection → prospect discovery → multi-criteria qualification scoring → personalized outreach drafting.
- **Fit Scoring:** 5-criteria objective score (0–100): vertical match (25%), geographic relevance (20%), business profile (20%), indemnity risk need (20%), public info quality (15%).
- **Verification:** Demo profiles are clearly separated from live queries. No contact details or email addresses are fabricated.

---

## Multilingual Support

- **Current Implementation:** English language generation, compliance checking, and human review are fully implemented and verified.
- *Note:* Do not claim full automated localization for additional regional languages unless verified with specialized regulatory rubrics.

---

## Database-Driven Analytics

All dashboard metrics are computed dynamically from SQLite transactions:
- **Total Marketing Assets:** Count of all generated assets in `content_queue`.
- **Pending Review:** Items awaiting human review.
- **Approved / Scheduled Assets:** Approved items signed off by reviewers.
- **Rejected Assets & Rejection Rate:** Overall and cycle-by-cycle rejection percentage (`rejected / total_reviewed * 100`).
- **Risk Score Distribution:** Real-time risk scoring across Low, Medium, and High categories.
- **Risk Heatmap Matrix:** Visual matrix aggregating issue types across brands and platforms from actual review records.
- *No hardcoded statistics or mock percentages are used in reporting.*

---

## Security & Privacy

- **Environment Isolation:** Secrets configured in `.env` (excluded via `.gitignore`). Template committed as `.env.example`.
- **Zero Committed Secrets:** Repository contains zero hardcoded API keys or private tokens.
- **Human Approval Mandatory:** No automated publishing pipeline can bypass human sign-off.
- **Audit Logging:** Every generation, edit, approval, and rejection records timestamps, model metadata, and reviewer notes.

---

## Testing & Verification

The test suite contains 102 comprehensive integration and unit tests covering all system components:

```bash
pytest tests/ -v
```

### Test Coverage Areas:
- `tests/test_api.py`: FastAPI routes, health checks, generation, review approval, rejection, and lead endpoints.
- `tests/test_audit_fixes.py`: Database migrations, analytics calculations, brand validation, and topic preservation.
- `tests/test_compliance.py`: Brand rubrics, deterministic pattern matching, and fearmongering detection.
- `tests/test_content_generation_topics.py`: Topic awareness, prompt structure, variant diversity, and API flow.
- `tests/test_database.py`: SQLite transactions, approval state machine, and rejection rate math.
- `tests/test_end_to_end_audit_scenario.py`: Full 21-step provenance and feedback loop audit scenario.
- `tests/test_feedback_loop.py`: 10-step reviewer rejection, embedding, and regenerated copy verification.
- `tests/test_groq_guardrails.py`: XML prompt isolation, schema enforcement, repair retries, and claim grounding.
- `tests/test_hallucination_suite.py`: Anti-hallucination guarantees, injection defense, and brand isolation.
- `tests/test_human_edit_persistence.py`: Human edit persistence, database reloads, compliance re-checks, and approval gates.
- `tests/test_rag_and_risk_intelligence.py`: PDF ingestion, vector hybrid search, and risk heatmap analytics.

---

## Known Limitations

1. **Live Web Research:** Live competitor research requires a valid `TAVILY_API_KEY`. Without it, the agent operates in verified offline competitor analysis mode.
2. **External Image Generation:** Generating AI images requires an external API key (e.g. OpenAI or custom provider). In its absence, structured text prompts and SVG/canvas previews are generated.
3. **Local ChromaDB:** The vector store operates locally via SQLite/file storage in `data/chromadb/`. Multi-process writes should be synchronized in high-concurrency environments.
4. **Database Architecture:** SQLite is utilized for transactional integrity, audit trails, and local zero-dependency deployment. For multi-region enterprise scaling, migration to PostgreSQL is recommended.
