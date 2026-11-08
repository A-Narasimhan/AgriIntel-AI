# AgriIntel AI â€” Team A Implementation & Experiments Handover

**Target Audience:** Amaravadi Narasimhan & Sangaraboina Sai Teja (Team A)
**Project Phase:** Pre-Exam Freeze (Nov 8, 2026) $\to$ Post-Exam Execution (Dec 10, 2026 onwards)
**Active Integration Branch:** `integration/audit-consolidated`
**Reference Commit:** `0ce76d6` (Merge: `teammate-llm-frontend` into `integration/audit-consolidated`)

---

## 1. Executive Summary & Freeze Status

As of **November 8, 2026**, the AgriIntel AI codebase is in a stable **Pre-Exam Freeze**. All teammate contributions from `teammate-kb` (curated ICAR PDFs, multi-crop RAG, interaction dataset export, modular UI) and `teammate-llm-frontend` (dynamic provider, intent propagation, robust API parsing) are fully integrated and verified on `integration/audit-consolidated`.

During the examination period (Nov 10 â€“ Dec 10, 2026), **no code changes or database rebuilds should occur**. This document provides Team A with an exact roadmap to execute immediately following exams.

---

## 2. Current Architecture & Working Features

```text
Farmer Query + Crop + Location
          â”‚
          â–¼
QueryUnderstandingService  â”€â”€â–º Crop extraction, intent (7 categories), stage extraction,
                               and cross-crop conflict validation (HTTP 400)
          â”‚
          â–¼
RetrievalService           â”€â”€â–º all-MiniLM-L6-v2 query embedding
                               ChromaDB HNSW cosine similarity
                               Crop metadata filter
                               Candidate expansion (k >= 10, disease k >= 20)
                               Intent-specific lexical filtering
                               Disease bipartite ranking (symptom vs. management)
          â”‚
          â–¼
WeatherService             â”€â”€â–º Open-Meteo geocoding & 3-day forecast
                               Non-blocking fallback context
          â”‚
          â–¼
LLMService                 â”€â”€â–º Anti-hallucination grounding gate (_has_relevant_evidence)
                               Multi-aspect disease verification
                               Provider router (Gemini, OpenAI, Groq, or Offline synthesis)
                               Source provenance builder (file, title, page, excerpt)
          â”‚
          â–¼
FastAPI Advisory Endpoint  â”€â”€â–º JSON response with advisory, sources, weather, grounding flag
          â”‚
          â–¼
DatasetService             â”€â”€â–º SQLite logging (data/interactions.db)
                               Export endpoint: GET /interactions/export?format=jsonl|csv
```

### Verified Working Capabilities
1. **Multi-Crop Support**: Rice, Cotton, Maize, Groundnut, Soybean.
2. **Crop Conflict Rejection**: Requesting "blast disease in groundnut" while selecting "soybean" immediately returns `HTTP 400 Bad Request`.
3. **Intent-Guided Candidate Expansion**: Expands candidate pool ($k \ge 10$) before applying intent lexical filters to prevent premature truncation.
4. **Bipartite Disease Grounding**: Queries requesting both symptoms and control require evidence covering both aspects; otherwise, the response is explicitly flagged as ungrounded (`is_evidence_grounded = false`).
5. **Dynamic Weather Context**: Open-Meteo real-time temperature, humidity, precipitation, and 3-day trend are injected into prompt/synthesis.
6. **Interaction Dataset Curation**: Automatic SQLite logging with filtered retrieval and JSONL/CSV file export.
7. **Frontend Dashboard**: Modular React 19 UI with real-time feedback, presets, and error parsing.

---

## 3. Known Bugs, Limitations & Technical Debt

1. **ChromaDB Chunk ID Drift (Priority: Moderate)**
   - Stored collection in `data/chroma/` holds 1,205 vectors generated via legacy character-based overlap.
   - The current chunker in `app/rag/chunker.py` uses sentence-boundary overlap, which produces 1,134 expected chunk IDs.
   - *Guideline:* **Do NOT rebuild or delete `data/chroma/` before running initial baseline evaluations.** Run evaluations against the existing stable store first.
2. **Scanned Pink Bollworm Leaflet (`cotton_pbw_management_cicr.pdf`) (Priority: High)**
   - This single-page CICR leaflet contains scanned raster images without a selectable text layer.
   - Currently skipped by `requires_ocr: true` in `sources.json`.
   - *Action Required:* Run Tesseract OCR or PyMuPDF OCR to extract text and index it.
3. **SentenceTransformer Cold-Start Latency (Priority: Low)**
   - PyTorch DLL initialization on Windows takes 15â€“20 seconds on cold start. In development and testing, run tests with pre-warmed sessions or focused module targets.

---

## 4. Evaluation Configurations & Experimental Setup

To provide Team B with publishable experimental data, Team A must evaluate **4 distinct retrieval configurations** across the 20 benchmark queries in `data/evaluation/benchmark_queries.json`:

| Config | Configuration Name | Description / Pipeline Logic |
|---|---|---|
| **A** | **Baseline Semantic Retrieval** | Naive dense vector retrieval: Query embedding $\to$ ChromaDB cosine search ($k=5$) **without** crop filter and **without** intent filter. |
| **B** | **Crop-Filtered Semantic Retrieval** | Dense vector retrieval with strict crop metadata constraint: `metadata["crop"] == target_crop`, returning top-5. |
| **C** | **Crop + Intent Filtered Retrieval** | Dense retrieval with crop constraint, expanded candidate pool ($k=10$), filtered by detected intent keywords (`pest`, `disease`, `irrigation`, `nutrient`, etc.). |
| **D** | **Full AgriIntel AI Pipeline** | Crop filter + candidate expansion ($k \ge 10$) + intent filter + disease bipartite ranking + regional filtering + grounding gate. |

### Evaluation Metrics to Measure
1. **Precision@5 ($P@5$):**
   $$\text{Precision@5} = \frac{\text{Count of relevant retrieved passages in top 5}}{5}$$
   *Relevance criterion:* Passage must match target crop AND contain specific information answering the query intent.
2. **Recall@5 ($R@5$):**
   $$\text{Recall@5} = \frac{\text{Count of expected key topics retrieved in top 5}}{\text{Total expected topics in benchmark}}$$
3. **Mean Reciprocal Rank (MRR):**
   $$\text{MRR} = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{1}{\text{rank}_i}$$
   where $\text{rank}_i$ is the rank of the first relevant passage for query $i$.
4. **Groundedness / Faithfulness Rate (%):**
   Percentage of advisory claims directly backed by cited ICAR page excerpts.
5. **Hallucination Refusal Accuracy (%):**
   Percentage of unanswerable or contradictory queries correctly returning a grounded refusal.
6. **Latency (ms):**
   Query embedding time, ChromaDB query time, reranking time, and total retrieval time.

---

## 5. Suggested Implementation Order (Post-Dec 10, 2026)

### Milestone 1: Automated Evaluation Harness (Days 1â€“3)
- **Goal:** Create an automated evaluation script that benchmarks all 4 configurations without manual testing.
- **New File:** `scripts/run_rag_evaluation.py`
- **Output:** Save results to `data/evaluation/evaluation_results.json` and a formatted console summary.
- **Verification:** Run `python scripts/run_rag_evaluation.py` and verify all 20 queries are evaluated under Configurations A, B, C, and D.

### Milestone 2: Pink Bollworm OCR Integration (Days 4â€“5)
- **Goal:** Extract text from `data/knowledge_base/cotton/cotton_pbw_management_cicr.pdf`.
- **Files to Modify:**
  - `scripts/build_knowledge_base.py` (or a dedicated OCR script `scripts/ocr_scanned_sources.py`).
  - `data/knowledge_base/sources.json` (update `ocr_status: "complete"` and `requires_ocr: false`).
- **Verification:** Query cotton pink bollworm management and confirm chunk retrieved from `cotton_pbw_management_cicr.pdf`.

### Milestone 3: Frontend Interactions UI (Days 6â€“7)
- **Goal:** Provide an in-app viewer and export interface for logged farmer interactions.
- **Files to Modify:**
  - `frontend/src/App.jsx`
  - `frontend/src/components/InteractionsModal.jsx` (new component)
- **Features:** Table view of recent interactions with filter dropdowns (crop, intent) and buttons to download `interactions.jsonl` and `interactions.csv`.
- **Verification:** `npm run build` passes with zero errors; interaction download verified in browser.

### Milestone 4: Final Test Suite Run & Metrics Handover (Days 8â€“9)
- **Goal:** Execute full regression suite, compile LaTeX tables, and hand over metric data to Team B.
- **Deliverables:** Export LaTeX tables of $P@5$, $R@5$, MRR, and Latency for Team B's research paper draft.

---

## 6. Files That Need Modification

```text
AgriIntel-AI/
â”œâ”€â”€ scripts/
â”‚   â”œâ”€â”€ run_rag_evaluation.py       [CREATE] Automated benchmark runner (Configs A, B, C, D)
â”‚   â”œâ”€â”€ ocr_scanned_sources.py     [CREATE] OCR utility for scanned ICAR leaflets
â”‚   â””â”€â”€ test_retrieval.py          [UPDATE] Optional helper updates
â”œâ”€â”€ data/
â”‚   â”œâ”€â”€ evaluation/
â”‚   â”‚   â”œâ”€â”€ benchmark_queries.json  [PRESERVE] 20 benchmark evaluation queries
â”‚   â”‚   â””â”€â”€ evaluation_results.json [GENERATE] Automated metrics output
â”‚   â””â”€â”€ knowledge_base/
â”‚       â””â”€â”€ sources.json           [UPDATE] Set requires_ocr: false after OCR
â””â”€â”€ frontend/
    â””â”€â”€ src/
        â”œâ”€â”€ App.jsx                [UPDATE] Add interaction modal trigger
        â””â”€â”€ components/
            â””â”€â”€ InteractionsModal.jsx [CREATE] Export and inspection modal
```

---

## 7. Test Plan & Regression Gates

Run these verification commands after each milestone:

```powershell
# 1. Fast unit regression tests (Dataset, Chunker, Query Understanding)
.venv\Scripts\pytest.exe tests/test_chunker.py tests/test_dataset.py tests/test_query_service.py

# 2. End-to-end Advisory Pipeline regression
.venv\Scripts\pytest.exe tests/test_advisory_pipeline.py

# 3. Frontend static linting and production build
npm --prefix frontend run lint
npm --prefix frontend run build

# 4. Experimental evaluation execution
python scripts/run_rag_evaluation.py
```

---

## 8. Summary Checklist Before Freeze

- [x] Working on branch `integration/audit-consolidated`.
- [x] Zero unstaged modifications in core application code.
- [x] All 27 core regression tests passing.
- [x] Frontend linting passing (0 warnings, 0 errors).
- [x] Frontend build succeeding in $< 500\text{ ms}$.
- [x] Original teammate branches intact.
- [ ] Push `integration/audit-consolidated` to remote origin (pending user authorization).
