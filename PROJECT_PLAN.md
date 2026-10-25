# AgriIntel AI - Current Project Plan

## Objective

AgriIntel AI is a retrieval-augmented agricultural advisory system for:

- Rice
- Cotton
- Maize
- Groundnut
- Soybean

It combines deterministic query understanding, curated agricultural documents,
crop-filtered ChromaDB retrieval, Open-Meteo weather context, a configurable
LLM/offline synthesis layer, source citations, and SQLite interaction logging.

## Architecture

```text
Farmer query + selected crop + location
                |
                v
QueryUnderstandingService
  crop, intent, growth-stage extraction and crop-conflict validation
                |
                v
EmbeddingService -> persistent ChromaVectorStore
  crop metadata filter, intent filter, disease/task relevance ranking
                |
                v
WeatherService -> Open-Meteo (optional location context)
                |
                v
LLMService
  evidence sufficiency check -> provider call or offline grounded synthesis
                |
                v
Advisory response with citations
                |
                v
DatasetService -> data/interactions.db
```

The vector store and interaction database are separate. Retrieval preserves
source filename, title, crop, page, year, topic, and similarity score.
Chunking preserves page boundaries and now prefers sentence-boundary overlap.

## Implemented

### Backend and API

- FastAPI application, CORS, health endpoint, and OpenAPI documentation.
- Pydantic request and response schemas.
- Crop normalization for all five supported crops.
- Deterministic extraction of crop, intent, and growth stage.
- Selected-crop versus query-crop conflict validation before weather, retrieval,
  or interaction logging.
- Persistent ChromaDB vector store with crop metadata filtering.
- Sentence-transformers `all-MiniLM-L6-v2` query/document embeddings.
- Page-aware PyMuPDF ingestion and metadata preservation.
- Open-Meteo geocoding and forecast integration.
- Configurable Gemini, OpenAI, Groq, and offline/mock synthesis paths.
- SQLite interaction logging and inspection/export endpoints.

### Retrieval and grounding

- Candidate-pool expansion before intent filtering.
- Disease retrieval requires the named disease in passage text rather than
  relying only on a broad document topic label.
- Tikka queries recognize explicit groundnut leaf-spot wording as the relevant
  passage synonym.
- Relevance ranking favors disease symptoms and management evidence.
- Results are not padded with passages that fail the requested intent.
- Combined symptoms-and-management queries require both evidence aspects across
  the eligible retrieved passages.
- Crop-correct but unsupported queries are reported as ungrounded.
- Source references include source ID, title, crop, page, year, and excerpt.

### Frontend

- React 19 + Vite frontend with the accepted professional redesign.
- Advisory form, crop/location/query context, weather context, citations, and
  interaction-oriented presentation.

## Actual API surface

- `GET /health`
- `POST /advisory`
- `POST /retrieve`
- `GET /weather?location=...`
- `GET /crops`
- `GET /interactions`
- `GET /interactions/export`
- `GET /docs`

The current development commands use backend port `8001` and frontend port
`5173`:

```powershell
# From D:\AgriIntel-AI
uvicorn app.main:app --reload --port 8001

# In a second terminal
cd frontend
npm run dev -- --port 5173
```

## Verification status

### Tested

- Focused Python regression suite: 42 tests passing.
- Crop-conflict API test: soybean selected with a groundnut query returns HTTP
  400 before weather/retrieval/logging.
- Rice blast and groundnut tikka retrieval regressions using temporary in-memory
  stores.
- Combined disease query:
  - symptoms-only evidence is ungrounded;
  - separate symptom and management evidence can jointly ground the answer.
- Generic crop-context and unrelated disease passages are rejected by grounding.
- Sentence-aware chunk overlap regression.

### Real persistent-data verification completed

The existing `data/chroma` collection was queried read-only; it was not rebuilt,
cleared, or replaced.

- Rice blast symptoms and management: grounded, four returned passages from
  `rice_production_and_protection.pdf`, led by pages 33, 87, and 32.
- Groundnut tikka symptoms and management: grounded, four returned passages from
  `groundnut_protection_technologies_iigr.pdf`, led by pages 29, 7, and 9.
- Rice drone-model query: returned crop-matching passages but was not grounded
  because the evidence does not answer the specific model-selection question.
- Soybean selected with a groundnut query: HTTP 400 clarification response.

The real-data checks printed passage text, source filename, page, topic, and
similarity score. They also exposed that some source PDFs contain broad,
multi-topic pages and metadata labels; this remains a knowledge-base quality
limitation even after relevance filtering.

### Partially verified

- Real persistent retrieval has been checked for rice blast and groundnut
  tikka, but the complete five-crop disease/intention benchmark has not been
  rerun as a formal evaluation.
- Offline/mock synthesis is covered locally. External Gemini/OpenAI/Groq calls
  are configuration-dependent and were not required for the focused tests.
- Frontend lint/build validation is a required release check and should be run
  after frontend dependencies are available.

### Pending

- Formal retrieval precision/recall evaluation across the benchmark queries.
- Human review of advisory usefulness and citation correctness for every crop.
- OCR and indexing of the scanned cotton pink-bollworm leaflet listed in the
  source registry (`ocr_status: pending`).
- Review and possible replacement of broad or mixed-topic source PDFs with
  section-level authoritative documents.
- Production deployment, authentication, rate limiting, monitoring, and
  secrets management.
- Confirmation of individual team-member contributions; the repository does
  not provide reliable evidence for assigning completed work to individuals.

## Source-document status

`data/knowledge_base/sources.json` is the source registry. It currently
contains ICAR/ICAR-institute entries for all five crops, including:

- ICAR Kharif Agro-Advisories for rice, cotton, maize, groundnut, and soybean.
- ICAR-CICR cotton technologies and pink-bollworm leaflet.
- ICAR-DGR groundnut production and crop-protection technologies.

The indexed persistent Chroma data is present and contains real extracted
passages. The registry also explicitly records that the scanned cotton
pink-bollworm leaflet still requires OCR; it must not be described as fully
indexed until that work is completed.

## Team responsibilities

The following are project-role responsibilities, not claims about completed
individual contributions:

- **AI/backend lead:** application architecture, FastAPI integration, query
  understanding, RAG pipeline, grounding, provider integration.
- **Knowledge-base owner:** authoritative document collection, source registry,
  extraction quality, metadata, and crop coverage.
- **Weather/dataset owner:** Open-Meteo integration, weather fallback behavior,
  SQLite schema, interaction logging, and export/inspection.
- **Frontend/testing owner:** React/Vite interface, API integration, regression
  tests, evaluation harness, and documentation support.

All contributors should understand the evidence-grounding limitations before
presenting recommendations as production-ready.

## Constraints and known issues

- Agricultural recommendations must come from retrieved evidence; unsupported
  questions must remain ungrounded.
- Weather is dynamic and can fail independently of static knowledge retrieval.
- A page can contain multiple crops, regions, or topics; metadata and passage
  quality require continued review.
- Similarity scores are Chroma cosine similarities, not calibrated confidence
  probabilities.
- The current offline synthesizer summarizes retrieved excerpts; it does not
  replace agronomist review.
- The live interaction database must not be reset during development
  validation.
- Knowledge-base rebuilds are deliberate maintenance operations and are not
  part of ordinary tests.

## Validation commands

```powershell
# Focused backend checks
pytest -q tests/test_retrieval_service.py tests/test_advisory_pipeline.py `
  tests/test_query_service.py tests/test_chunker.py

# Diff hygiene
git --no-pager diff --check

# Frontend checks
cd frontend
npm run lint
npm run build
```
