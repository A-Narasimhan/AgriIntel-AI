# AgriIntel AI — Branch Integration and Implementation Status Audit

**Project:** AgriIntel AI: Smart Agricultural Advisory and Dataset Generation from Farmer Queries and Weather Intelligence  
**Scope:** 4-Member B.Tech Major Project (Based on the *CottonBot* Research Paper)  
**Audit & Integration Date:** November 7, 2026  
**Integration Target Branch:** `integration/audit-consolidated`  
**Primary Auditor:** Senior Software Engineer, Git Integration Specialist & Technical Auditor  

---

## 1. Repository and Branch Inventory

### 1.1 Environment & Working Tree Status
- **Root Directory:** `D:\AgriIntel-AI`
- **Initial Working Branch:** `teammate-kb` (ahead of `origin/teammate-kb` by 4 commits)
- **Local Branches:**
  - `main` (`2582b7e` — Initial commit)
  - `implementation-checkpoint` (`7918579` — Add AgriIntel AI implementation checkpoint)
  - `teammate-kb` (`12cfbb8` — feat: improve AgriIntel AI dashboard)
  - `teammate-llm-frontend` (`626b91c` — frontend integration)
  - `integration/audit-consolidated` (`0ce76d6` — Integrated consolidation branch)
- **Remote Branches (`origin`):**
  - `origin/main` (`2582b7e`)
  - `origin/implementation-checkpoint` (`7918579`)
  - `origin/teammate-kb` (`6401d2b` — Fix PDF text normalization and expand retrieval candidate pool)
  - `origin/teammate-llm-frontend` (`626b91c` — frontend integration)

### 1.2 Team Authors Discovered in Git History
1. **A-Narasimhan / Narasimhan (`narasimhanamaravadi7@gmail.com`):**
   - Core architecture, FastAPI server, query understanding, RAG chunker/vector store, Open-Meteo weather integration, SQLite interaction dataset persistence & export, anti-hallucination grounding gates, modular React dashboard redesign.
2. **pallapuakhila (`akhilapallapu10@gmail.com`):**
   - Knowledge base curation across 5 crops (Rice, Cotton, Maize, Groundnut, Soybean) with official ICAR/institute PDFs, source registry (`data/knowledge_base/sources.json`), knowledge base audit script (`data/audit_kb.py`), and retrieval verification script (`data/verify_retrieval_metadata.py`).
3. **Laaibahtazaeen (`b23cs089@kitsw.ac.in`):**
   - Branch `teammate-llm-frontend`: LLM service dynamic provider property, intent parameter threading into advisory generation, expanded intent vocabulary (weed, cultivation, harvesting, mite, mosaic, virus, zinc), robust frontend API client (configurable `VITE_API_BASE`, Pydantic error parsing for arrays/objects, non-JSON response fallbacks, crop hint).
4. **4th Team Member:**
   - No separate Git branch or commits found under a distinct 4th author name in the repository. The project plan identifies 4 designated project roles:
     - AI/Backend Lead
     - Knowledge-Base Owner
     - Weather/Dataset Owner
     - Frontend/Testing & Evaluation Owner
   - As documented in Section 13 below, the 4th teammate's responsibilities align with the formal evaluation and research-paper writing track.

---

## 2. Branch-by-Branch Contribution Table

| Branch | Author(s) | Key Commits | Features Implemented | Files Changed | Dependencies / API Changes |
|---|---|---|---|---|---|
| `main` | Narasimhan | `2582b7e` | Initial project scaffolding | Basic workspace structure | None |
| `implementation-checkpoint` | A-Narasimhan | `7918579` | Complete Phase 1 MVP: FastAPI backend, PyMuPDF RAG, ChromaDB cosine store, Open-Meteo service, SQLite interactions, 20-query evaluation benchmark, 19 baseline tests | 56 files (`app/`, `tests/`, `scripts/`, `data/`, `frontend/`) | FastAPI 0.115, Pydantic v2, ChromaDB, Sentence-Transformers, PyMuPDF |
| `teammate-kb` | pallapuakhila, A-Narasimhan | `35e0efb`, `4436b76`, `792c631`, `6401d2b`, `8f1d570`, `4a9934c`, `be872c3`, `12cfbb8` | 1. 5-crop ICAR PDF literature and registry<br>2. KB audit & retrieval verification tools<br>3. Glyph ligature normalization (`\u03d0` $\to$ `fl`)<br>4. Cross-crop chunk filtering (`is_chunk_relevant_to_crop`)<br>5. Scanned PDF OCR skip guard<br>6. Crop-conflict validation (HTTP 400 on mismatched selection)<br>7. Strict multi-aspect disease grounding (symptoms vs. management)<br>8. SQLite interaction dataset filtering & export (`/interactions/export` as JSONL/CSV)<br>9. Complete React 19 modular dashboard redesign with 8 subcomponents | 65+ files modified/added | Added `/interactions/export` (JSONL/CSV); Pydantic schemas updated for exports and filters |
| `teammate-llm-frontend` | Laaibahtazaeen | `626b91c` (branched from `6401d2b`) | 1. Dynamic LLM provider property (`@property def provider`)<br>2. Threading of detected `intent` into `generate_advisory`<br>3. Expanded keyword dictionaries for `pest`, `disease`, `nutrient`, `weed`, `cultivation`, `harvesting`<br>4. OpenAI provider routing guard fix<br>5. Frontend dynamic `VITE_API_BASE`<br>6. Pydantic validation error parsing (handling list of dicts, objects, strings)<br>7. Non-JSON server error fallback | `app/api/advisory.py`<br>`app/services/llm_service.py`<br>`frontend/src/App.jsx` | Environment variable `VITE_API_BASE` supported in frontend |

---

## 3. Duplicate and Conflicting Implementation Analysis

### 3.1 Divergence Root Cause
Both branches diverged from commit `6401d2b` (`Fix PDF text normalization and expand retrieval candidate pool`):
- `teammate-kb` advanced by 4 commits (`8f1d570`, `4a9934c`, `be872c3`, `12cfbb8`), heavily rewriting `App.jsx` into a modular multi-card layout and introducing multi-factor disease aspect grounding and dataset exports.
- `teammate-llm-frontend` modified the legacy monolithic `App.jsx` and added error handling, while adding intent wiring and keyword expansions in `llm_service.py`.

### 3.2 Conflict Breakdown & Resolution

1. **`app/api/advisory.py`:**
   - *teammate-llm-frontend:* Added `intent=intent` parameter to `llm_service.generate_advisory(...)`.
   - *teammate-kb:* Already included `intent=intent`, PLUS added crop-conflict validation, `/interactions/export`, and query parameters for dataset filtering.
   - *Resolution:* Preserved `teammate-kb`'s full route logic. Both teammates intended the exact same `intent` parameter passing.

2. **`app/services/llm_service.py`:**
   - *teammate-llm-frontend:* Changed `self.provider` in `__init__` to dynamic `@property def provider(self) -> str: return (settings.llm_provider or "mock").lower()`. Expanded keyword lists (`weed`, `cultivation`, `harvesting`, `mite`, `mosaic`, `virus`, `zinc`). Fixed OpenAI condition to strictly require `self.provider == "openai"`.
   - *teammate-kb:* Introduced fine-grained disease aspect parsing (`_has_disease_evidence`, `_requested_disease_aspect_terms`, symptom-vs-management bipartite requirements) and offline structured synthesis.
   - *Resolution:* Combined both. Adopted the dynamic `@property def provider`, the OpenAI routing fix, and incorporated all missing vocabulary tokens (`mite`, `mosaic`, `virus`, `zinc`) into the grounding gate while preserving `teammate-kb`'s multi-aspect disease verification.

3. **`frontend/src/App.jsx`:**
   - *teammate-llm-frontend:* Modified the old single-file layout to support `import.meta.env.VITE_API_BASE`, robust Pydantic `detail` parsing, non-JSON response handling, and `(or mention in query)` label note.
   - *teammate-kb:* Migrated UI to React 19 modular design (`Header`, `WeatherCard`, `AdvisoryCard`, `SourcesCard`, `KnowledgeBaseStatus`, `Icons`, presets).
   - *Resolution:* Integrated all functional logic from `teammate-llm-frontend` (`VITE_API_BASE`, robust error parser, non-JSON protection, label guidance) directly into `teammate-kb`'s modern modular dashboard.

---

## 4. Integration and Merge Summary

- **Strategy:** Safe, non-destructive forward integration.
- **Actions Executed:**
  1. Created branch `integration/audit-consolidated` from `teammate-kb`.
  2. Synthesized compatible improvements from `teammate-llm-frontend` into `app/services/llm_service.py` and `frontend/src/App.jsx`.
  3. Committed integrated changes as `56769b3` (*feat(integration): consolidate teammate-kb and teammate-llm-frontend features*).
  4. Executed `git merge -s ours teammate-llm-frontend` (merge commit `0ce76d6`) to officially record branch convergence in the Git DAG.
  5. Verified zero unstaged changes and preserved all original local and remote branches.

---

## 5. Integrated Application Architecture

```text
                                  Farmer Query
                    (e.g., "Tikka disease control in groundnut")
                                       │
                                       ▼
                   ┌────────────────────────────────────────┐
                   │        FastAPI Application Layer       │
                   │   POST /advisory     POST /retrieve    │
                   │   GET  /weather      GET  /crops       │
                   │   GET  /interactions (filter & export) │
                   └───────────────────┬────────────────────┘
                                       │
                                       ▼
                   ┌────────────────────────────────────────┐
                   │        QueryUnderstandingService       │
                   │  • Crop Extraction & Normalization     │
                   │  • Cross-Crop Conflict Check (HTTP 400)│
                   │  • Intent Detection (7 categories)     │
                   │  • Growth-Stage Extraction             │
                   └───────────────────┬────────────────────┘
                                       │
                ┌──────────────────────┴──────────────────────┐
                │                                             │
                ▼                                             ▼
  ┌───────────────────────────┐                 ┌───────────────────────────┐
  │     RetrievalService      │                 │       WeatherService      │
  │ • Query Embedding         │                 │ • Open-Meteo Geocoding    │
  │   (all-MiniLM-L6-v2)      │                 │ • 3-Day Forecast & Alert  │
  │ • ChromaDB (HNSW Cosine)  │                 │ • Temperature / Humidity  │
  │ • Crop Metadata Filter    │                 │ • Graceful Fallback       │
  │ • Candidate Pool (k >= 10)│                 └─────────────┬─────────────┘
  │ • Intent Relevance Filter │                               │
  │ • Disease Aspect Ranking  │                               │
  └─────────────┬─────────────┘                               │
                │                                             │
                └──────────────────────┬──────────────────────┘
                                       │
                                       ▼
                   ┌────────────────────────────────────────┐
                   │            LLMService Layer            │
                   │  • Anti-Hallucination Grounding Gate   │
                   │    (Multi-aspect & Intent validation)  │
                   │  • Provider Routing                    │
                   │    (Gemini / OpenAI / Groq / Offline)  │
                   │  • Source Provenance Citation Builder  │
                   └───────────────────┬────────────────────┘
                                       │
                                       ▼
                   ┌────────────────────────────────────────┐
                   │         Advisory Response Model        │
                   │  • Actionable Agronomic Advisory       │
                   │  • Evidence Grounded Flag (True/False) │
                   │  • Source Documents & Page Numbers     │
                   │  • Weather Observation Summary         │
                   └───────────────────┬────────────────────┘
                                       │
                                       ▼
                   ┌────────────────────────────────────────┐
                   │         DatasetService Persistence     │
                   │  • SQLite interactions.db              │
                   │  • Log Query, Crop, Weather, Advisory  │
                   │  • Export to JSONL / CSV for Research  │
                   └────────────────────────────────────────┘
```

---

## 6. CottonBot versus AgriIntel AI Comparison

| Feature / Dimension | CottonBot (Base Paper: Kandamali et al., 2024) | AgriIntel AI (Current Implementation) | Classification | Architectural Impact |
|---|---|---|---|---|
| **Target Crop Scope** | Single crop: Cotton only | Multi-crop: Rice, Cotton, Maize, Groundnut, Soybean | **New AgriIntel AI Extension** | Requires cross-crop contamination filters, crop metadata routing, and query-crop conflict detection. |
| **Knowledge Base** | Cotton extension publications | Official ICAR institute publications (ICAR-CICR, ICAR-NRRI, ICAR-IIMR, ICAR-DGR, ICAR-IISR) | **Adapted Implementation** | Curated across 5 staple Indian crops; page-level provenance preserved. |
| **Vector DB & Search** | LangChain / Vector Store | Persistent ChromaDB with HNSW Cosine Similarity | **Adapted Implementation** | Embedded locally with `sentence-transformers/all-MiniLM-L6-v2`. |
| **Dynamic Weather** | Integrated Open-Meteo API | Integrated Open-Meteo API (Geocoding + Forecast + Fallback) | **Implemented as described** | Injects live temperature, humidity, precipitation, and 3-day trend into advisory context. |
| **Soil-Moisture IoT Sensors** | Real-time physical IoT soil sensor telemetry | None (No physical sensor integration or IoT telemetry in codebase) | **Not Implemented** | AgriIntel relies on Open-Meteo soil-drying/precipitation indicators rather than hardware probes. |
| **LSTM Forecasting** | LSTM neural network for temporal soil-moisture sequence forecasting | None (No LSTM, PyTorch sequence models, or weight files present) | **Not Implemented** | CottonBot’s LSTM forecasting was not ported; must **not** be claimed in the research paper. |
| **Agentic Irrigation Tools** | Function-calling tools for irrigation triggers | Rule-grounded irrigation intent checking from ICAR guidelines | **Adapted Implementation** | Replaces tool-use loops with deterministic intent grounding and weather-linked advisory synthesis. |
| **Hallucination Control** | System prompt instructions | 2-tier architectural guard: 1. Strict lexical & multi-aspect intent gate; 2. Hard refusal fallback on insufficient evidence | **New AgriIntel AI Extension** | Prevents ungrounded chemical dosage synthesis; verifiable via `is_evidence_grounded`. |
| **Query Disambiguation** | Assumes cotton context | Deterministic QueryUnderstandingService with conflict validation (HTTP 400 on crop mismatch) | **New AgriIntel AI Extension** | Essential for multi-crop integrity (e.g. user selects soybean but asks about groundnut tikka). |
| **Interaction Dataset Generation** | Chat logs | Structured SQLite persistence with query, detected metadata, weather, advisory, and JSONL/CSV export | **New AgriIntel AI Extension** | Purpose-built for downstream agricultural dataset curation and fine-tuning. |

> [!IMPORTANT]
> **Defensible Paper Positioning:** Do not claim that AgriIntel AI implemented LSTM networks or IoT soil sensors. The true, defensible technical contributions are:
> 1. Multi-crop query disambiguation and cross-crop contamination rejection.
> 2. Intent-aware, multi-aspect RAG retrieval with page-level ICAR provenance.
> 3. Two-tier anti-hallucination grounding gates refusing unverified agrochemical dosages.
> 4. Automated curation and export of structured farmer interaction datasets (JSONL/CSV).

---

## 7. Implemented / Partial / Missing Component Matrix

| Module | Component | Status | Evidence in Codebase |
|---|---|---|---|
| **Backend** | FastAPI app & CORS | **Fully Implemented** | `app/main.py` |
| | API routing & schemas | **Fully Implemented** | `app/api/routes.py`, `app/api/advisory.py`, `app/core/schemas.py` |
| | Centralized settings | **Fully Implemented** | `app/core/config.py`, `.env.example` |
| | Query conflict validation | **Fully Implemented** | `app/api/advisory.py` lines 43-52 (HTTP 400 on conflict) |
| **Knowledge Base & RAG** | PDF Ingestion & normalization | **Fully Implemented** | `app/services/ingestion_service.py` (PyMuPDF + glyph mapping) |
| | Chunking & sentence overlap | **Fully Implemented** | `app/rag/chunker.py` (sentence-aware boundary splitting) |
| | Cross-crop filter | **Fully Implemented** | `app/rag/chunker.py` (`is_chunk_relevant_to_crop`) |
| | Scanned PDF OCR guard | **Partially Implemented** | Scanned leaflet flagged `requires_ocr`; skip guard active, but OCR extraction itself is pending |
| | Vector Store & Cosine HNSW | **Fully Implemented** | `app/rag/vector_store.py` (1,205 stored vectors in `data/chroma`) |
| | Dense Embedding Service | **Fully Implemented** | `app/services/embedding_service.py` (`all-MiniLM-L6-v2`) |
| | Intent & Stage Extraction | **Fully Implemented** | `app/services/query_service.py` (7 intent classes + growth stages) |
| | Multi-Aspect Disease Retrieval | **Fully Implemented** | `app/services/retrieval_service.py` (disease symptom & management ranking) |
| **Advisory & LLM** | Evidence Grounding Gate | **Fully Implemented** | `app/services/llm_service.py` (`_has_relevant_evidence`, multi-factor check) |
| | Provider Abstraction | **Fully Implemented** | Gemini, OpenAI, Groq, and offline grounded synthesis |
| | Weather Integration | **Fully Implemented** | `app/services/weather_service.py` (Open-Meteo geocoding + 3-day forecast) |
| | LSTM Soil Forecasting | **Missing / Not Applicable** | Not present in codebase; do not claim |
| | Physical IoT Sensors | **Missing / Not Applicable** | Not present in codebase; do not claim |
| **Dataset Generation** | SQLite Interaction Logging | **Fully Implemented** | `app/services/dataset_service.py` (`data/interactions.db`) |
| | JSONL & CSV Dataset Export | **Fully Implemented** | `GET /interactions/export?format=jsonl|csv&crop=...&intent=...` |
| **Frontend** | React 19 + Vite Dashboard | **Fully Implemented** | `frontend/src/App.jsx` + modular components (`AdvisoryCard`, `WeatherCard`, `SourcesCard`, etc.) |
| | Preset Queries & Grounding Badges | **Fully Implemented** | Presets for 5 crops, verification status badges, source page citations |
| | Dynamic API Base & Robust Errors | **Fully Implemented** | `import.meta.env.VITE_API_BASE`, Pydantic error list parsing |
| **Evaluation** | Automated unit/regression suite | **Fully Implemented** | `tests/` (80 tests covering chunking, dataset, query, RAG, advisory) |
| | Formal Precision/Recall Benchmark | **Implemented but not executed** | `data/evaluation/benchmark_queries.json` exists; benchmark execution script pending |

---

## 8. Tests Executed and Actual Results

| Test Scope | Command / Tool | Items | Result | Duration | Notes |
|---|---|---|---|---|---|
| **Text Chunker & Metadata** | `pytest tests/test_chunker.py` | 6 tests | **PASSED** | ~12s | Verifies sentence boundaries, crop alias filtering, and chunk overlap. |
| **Interaction Dataset Persistence** | `pytest tests/test_dataset.py` | 16 tests | **PASSED** | ~34s | Verifies SQLite CRUD, JSONL formatting, CSV RFC-4180 compliance, filtering by crop and intent. |
| **Query Understanding** | `pytest tests/test_query_service.py` | 5 tests | **PASSED** | ~50s | Verifies crop extraction, crop conflict detection, intent classification, and growth stages. |
| **Combined Regression Check** | `pytest tests/test_chunker.py tests/test_dataset.py tests/test_query_service.py` | 27 tests | **27 PASSED, 0 FAILED** | 50.83s | Verified on `integration/audit-consolidated`. |
| **Frontend Static Analysis** | `npm --prefix frontend run lint` | 11 files | **PASSED** | 58ms | Oxlint passed with **0 errors, 0 warnings** across 104 rules. |
| **Frontend Production Build** | `npm --prefix frontend run build` | 24 modules | **PASSED** | 429ms | Vite compiled `dist/` cleanly (`index.html`, `index.css`, `index.js`). |
| **Full Historical Test Baseline** | Historical pytest run (`teammate-kb`) | 80 tests | **80 PASSED** | 431.20s | Full end-to-end suite passing in project baseline. |

---

## 9. Known Bugs, Limitations, and Technical Debt

1. **ChromaDB Chunk ID Drift:**
   - As documented in `CHROMADB_ID_DRIFT_ANALYSIS_20261030.md`, the currently stored 1,205 vectors in `data/chroma/` were generated with an earlier character-based chunker. Re-running `build_knowledge_base.py` with the modern sentence-boundary chunker recomputes 1,134 expected chunk IDs. While all source knowledge is retained, rebuilding the vector store should be done deliberately rather than inside automated test runs.
2. **Scanned Pink Bollworm PDF (`cotton_pbw_management_cicr.pdf`):**
   - The PDF contains scanned raster images without a selectable text layer. It is properly skipped by the ingestion guard (`requires_ocr: true`), but OCR with Tesseract or PyMuPDF OCR has not yet been applied.
3. **Broad Multi-Topic ICAR Pages:**
   - Some state/national package-of-practices PDFs contain pages where multiple crops or mixed topics are mentioned in the same section, occasionally introducing weak passage candidates prior to intent filtering.
4. **SentenceTransformer Cold-Start Latency:**
   - Loading `sentence-transformers/all-MiniLM-L6-v2` in Python 3.13 on Windows takes ~15–20 seconds on cold start due to PyTorch DLL initialization. In production, this service must run as a standing persistent daemon (Uvicorn).

---

## 10. Recommended Research Contribution

The strongest defensible research contribution beyond CottonBot is:

> **"Evidence-Grounded Multi-Crop Advisory with Crop-Intent Disambiguation and Automated Interaction Dataset Curation"**

### Why this contribution is scientifically defensible:
1. **Multi-Crop Domain Transfer:** CottonBot operated strictly on a mono-crop regime. Extending RAG to 5 major crops introduces severe cross-crop passage contamination (e.g., rice blast chemicals misapplied to groundnut). AgriIntel AI solves this via deterministic query understanding, crop conflict guards, and index-time crop filtering.
2. **Two-Tier Anti-Hallucination Grounding:** Rather than trusting an LLM system prompt alone, AgriIntel enforces a pre-generation lexical/aspect validation gate (`_has_relevant_evidence`). If authoritative ICAR evidence does not cover both symptom identification and chemical/cultural control, the system issues a verified refusal.
3. **Interaction-Driven Dataset Generation:** By capturing live farmer queries, resolved intents, weather context, retrieved passages, and grounding status into a structured dataset (`/interactions/export`), AgriIntel AI serves as an empirical data pipeline for fine-tuning smaller open-source agricultural LLMs (e.g., Llama-3-8B-Agri).

---

## 11. Controlled Evaluation Experiments Still Required

To publish a paper based on AgriIntel AI, the team must run a controlled empirical experiment across the 20 benchmark queries (`data/evaluation/benchmark_queries.json`):

### 11.1 Experimental Configurations
- **Baseline A (Naive Dense Semantic Retrieval):** Query embedded with `all-MiniLM-L6-v2`, top-$k$ retrieved via ChromaDB without metadata filtering.
- **System B (Crop-Filtered Semantic Retrieval):** Top-$k$ retrieval constrained strictly to `metadata["crop"] == target_crop`.
- **System C (Crop + Intent-Filtered Retrieval):** Candidate pool expanded to $k=10$, filtered by detected intent keywords (`pest`, `disease`, `irrigation`, `nutrient`, etc.).
- **System D (AgriIntel Full Pipeline):** Crop filtering + Intent candidate filtering + Multi-aspect disease bipartite ranking + Weather context injection + Grounding refusal gate.

### 11.2 Evaluation Metrics
1. **Precision@5:** Fraction of retrieved passages that are directly relevant to the specific query crop and intent.
2. **Recall@5:** Fraction of essential ICAR management recommendations retrieved in top-5.
3. **Mean Reciprocal Rank (MRR):** Reciprocal rank of the first genuinely relevant passage answering the farmer's question.
4. **Faithfulness / Groundedness Rate (%):** Percentage of generated responses whose claims are 100% supported by retrieved citations (evaluated via Ragas or agronomist human review).
5. **Hallucination Refusal Accuracy (%):** Ability of the system to refuse unanswerable or conflicting queries (e.g., asking for drone spray models not in ICAR docs).
6. **End-to-End Latency (ms):** Query-to-advisory latency under offline vs. cloud LLM synthesis.

---

## 12. Remaining Implementation Tasks

1. **Benchmark Evaluation Harness Script (`scripts/run_rag_evaluation.py`):**
   - Automatically iterate through `data/evaluation/benchmark_queries.json`.
   - Execute Baselines A, B, C, and Full Pipeline D.
   - Compute Precision@k, Recall@k, and MRR. Output results to `data/evaluation/evaluation_results.json` and a formatted LaTeX table.
2. **OCR Pipeline for Scanned Leaflet:**
   - Run Tesseract OCR on `data/knowledge_base/cotton/cotton_pbw_management_cicr.pdf` and update `sources.json` to mark `ocr_status: complete`.
3. **Frontend Interactions Inspection Screen:**
   - Add a tab or view in the React dashboard to inspect logged farmer interactions and download the JSONL/CSV dataset directly from the UI.

---

## 13. Prioritized 4-Member Team Work Breakdown

To maximize efficiency and complete both the major project implementation and the final research paper on schedule, divide the four team members into two specialized tracks:

### Track 1: Implementation & Experimental Evaluation (2 Members)

#### Member 1: AI & Retrieval Engineer (Lead)
- **Primary Tasks:**
  1. Build the evaluation harness script (`scripts/run_rag_evaluation.py`) to benchmark the 4 retrieval configurations (A, B, C, D) across all 20 queries in `benchmark_queries.json`.
  2. Log Precision@k, Recall@k, MRR, and latency metrics to CSV/JSON.
  3. Perform OCR on `cotton_pbw_management_cicr.pdf` to complete ICAR cotton knowledge base coverage.
  4. Ensure end-to-end integration stability on `integration/audit-consolidated`.

#### Member 2: Dataset, Weather & Frontend Engineer
- **Primary Tasks:**
  1. Add an "Interaction Dataset" view/tab to the React dashboard allowing one-click export of `interactions.jsonl` and `interactions.csv`.
  2. Implement Open-Meteo extreme weather warning cards (high rainfall / high wind advisories advising farmers against pesticide spraying).
  3. Run frontend production build tests and verify mobile responsiveness for rural smartphone viewports.
  4. Curate 50 realistic farmer queries across Telangana and Andhra Pradesh farming regions to populate the SQLite interaction database for experimental analysis.

---

### Track 2: Research Paper Writing & Documentation (2 Members)

#### Member 3: Paper Lead — Methodology, Architecture & RAG Formulation
- **Primary Tasks:**
  1. Write **Section 1: Introduction** — Problem statement of Indian agriculture, limitations of generic LLMs (hallucination of chemical doses, lack of regional ICAR grounding), and motivation for AgriIntel AI over CottonBot.
  2. Write **Section 3: System Architecture & Methodology**:
     - Mathematical formulation of RAG: Query embedding $\mathbf{q} = \mathcal{E}(x)$, candidate passage pool $\mathcal{C}_k$, and metadata filtering function $\mathcal{M}(c, \text{crop}, \text{intent})$.
     - Architectural diagrams illustrating the two-tier anti-hallucination grounding gate.
     - Formal comparison table between CottonBot and AgriIntel AI (using Section 6 of this audit).
  3. Write **Section 4: Authoritative Knowledge Base Construction** — Curation methodology of ICAR/ICAR-institute literature across Rice, Cotton, Maize, Groundnut, and Soybean.

#### Member 4: Paper Co-Lead — Experimental Results, Literature Review & Dataset Analysis
- **Primary Tasks:**
  1. Write **Section 2: Related Work** — Comprehensive review of agricultural LLMs (AgriBERT, FarmVibes, CottonBot, CropDoctor), contrasting AgriIntel’s multi-crop approach with CottonBot's single-crop IoT approach.
  2. Write **Section 5: Experimental Evaluation & Results**:
     - Take experimental output tables from Member 1 and format into publication-quality LaTeX tables comparing Baselines A, B, C, and D.
     - Plot Precision@k and MRR comparative bar charts.
     - Document qualitative case studies (e.g. Groundnut Tikka combined symptom-management query vs. out-of-scope drone query refusal).
  3. Write **Section 6: Interaction Dataset Characteristics & Conclusion**:
     - Statistical distribution of farmer queries by crop, intent, and grounding rate from the exported SQLite dataset.
     - Future work: fine-tuning domain SLMs (Small Language Models) using the generated interaction dataset.
