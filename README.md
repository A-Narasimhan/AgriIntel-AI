# AgriIntel AI

**Smart Agricultural Advisory and Dataset Generation from Farmer Queries and Weather Intelligence**

> B.Tech Final Year Major Project · Status: **Phase 1 (Foundation + RAG Infrastructure) Complete**

---

## What Is Implemented

| Component | Status |
|---|---|
| FastAPI backend + health endpoint | ✅ Working |
| Pydantic schemas for all request/response models | ✅ Done |
| `app/core/config.py` — centralized environment settings | ✅ Done |
| RAG chunker with page-boundary preservation | ✅ Done |
| ChromaDB vector store (crop-filtered retrieval) | ✅ Done |
| Embedding service — sentence-transformers/all-MiniLM-L6-v2 | ✅ Done |
| PDF ingestion service — PyMuPDF, page-by-page | ✅ Done |
| Weather service — Open-Meteo (geocoding + forecast) | ✅ Done |
| Query understanding — crop, intent, growth stage extraction | ✅ Done |
| LLM service — provider abstraction (Gemini / OpenAI / Groq / offline) | ✅ Done |
| Interaction dataset — SQLite logging | ✅ Done |
| `POST /advisory` — grounded end-to-end advisory pipeline | ✅ Done |
| `POST /retrieve` — RAG retrieval endpoint | ✅ Done |
| `GET /weather` — live weather context | ✅ Done |
| `GET /crops` — supported crop list | ✅ Done |
| `GET /interactions` — dataset inspection | ✅ Done |
| React + Vite frontend | ✅ Done |
| Evaluation benchmark queries (20 queries × 5 crops) | ✅ Done |
| pytest test suite (19 tests) | ✅ All passing |

**Knowledge base PDF documents**: awaiting genuine ICAR publications → place into `data/knowledge_base/<crop>/`

---

## Project Structure

```
AgriIntel-AI/
├── app/
│   ├── main.py               # FastAPI entrypoint + CORS
│   ├── api/
│   │   ├── routes.py         # /health + router mounting
│   │   ├── advisory.py       # /advisory, /weather, /interactions, /crops
│   │   └── retrieval.py      # /retrieve
│   ├── core/
│   │   ├── config.py         # Centralized environment settings
│   │   └── schemas.py        # All Pydantic schemas
│   ├── rag/
│   │   ├── chunker.py        # Page-aware text chunker
│   │   ├── metadata.py       # Crop normalization, chunk IDs, validation
│   │   └── vector_store.py   # ChromaDB persistent vector store
│   └── services/
│       ├── embedding_service.py   # Singleton sentence-transformers
│       ├── ingestion_service.py   # PyMuPDF PDF → chunks → embeddings → ChromaDB
│       ├── retrieval_service.py   # Query embedding + crop-filtered retrieval
│       ├── weather_service.py     # Open-Meteo geocoding + forecast
│       ├── query_service.py       # Crop/intent/stage extraction
│       ├── llm_service.py         # LLM provider abstraction (Gemini/OpenAI/Groq/offline)
│       └── dataset_service.py     # SQLite interaction dataset
├── data/
│   ├── knowledge_base/
│   │   ├── rice/             # Place ICAR-NRRI PDFs here
│   │   ├── cotton/           # Place ICAR-CICR PDFs here
│   │   ├── maize/            # Place ICAR-IIMR PDFs here
│   │   ├── groundnut/        # Place ICAR-DGR PDFs here
│   │   └── soybean/          # Place ICAR-IISR PDFs here
│   ├── sources.json          # Authoritative source registry metadata
│   ├── chroma/               # Persistent ChromaDB vector store (auto-created)
│   └── evaluation/
│       └── benchmark_queries.json  # 20-query evaluation benchmark
├── scripts/
│   ├── build_knowledge_base.py  # Index PDFs into ChromaDB
│   └── test_retrieval.py        # Run retrieval evaluation
├── tests/                        # pytest test suite (19 tests, all passing)
├── frontend/                     # React + Vite frontend
└── requirements.txt
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.13, FastAPI, Uvicorn |
| Validation | Pydantic v2, pydantic-settings |
| PDF Extraction | PyMuPDF (pymupdf) |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 |
| Vector Database | ChromaDB (persistent, local) |
| Weather | Open-Meteo API (httpx) |
| LLM Abstraction | Gemini / OpenAI / Groq / offline grounded synthesis |
| Dataset Storage | SQLite |
| Frontend | React 19 + Vite |
| Testing | pytest |

---

## Setup and Running

### 1. Activate virtual environment

```powershell
.venv\Scripts\Activate.ps1
```

### 2. Run the backend

```bash
uvicorn app.main:app --reload
```

### 3. Index agricultural PDFs (after placing genuine ICAR documents)

```bash
python scripts/build_knowledge_base.py
```

### 4. Run the frontend

```bash
cd frontend
npm run dev
```

Frontend: http://localhost:5173  
Backend API: http://localhost:8000  
Interactive API docs: http://localhost:8000/docs

### 5. Run tests

```bash
pytest
```

### 6. Run retrieval evaluation (after indexing PDFs)

```bash
python scripts/test_retrieval.py
```

---

## Adding Agricultural Source Documents

1. Obtain genuine PDF publications from ICAR research institutes:
   - Rice: ICAR-NRRI (https://icar-nrri.gov.in)
   - Cotton: ICAR-CICR (https://cicr.icar.gov.in)
   - Maize: ICAR-IIMR (https://iimr.icar.gov.in)
   - Groundnut: ICAR-DGR (https://dgr.icar.gov.in)
   - Soybean: ICAR-IISR (https://iisrindore.icar.gov.in)

2. Place the PDF files under the appropriate folder:
   ```
   data/knowledge_base/rice/your_icar_document.pdf
   data/knowledge_base/cotton/your_icar_document.pdf
   ```

3. Update `data/knowledge_base/sources.json` with matching metadata for each document.

4. Run the build script:
   ```bash
   python scripts/build_knowledge_base.py
   ```

---

## Configuring an LLM Provider

Copy `.env.example` to `.env` and set your preferred provider:

```
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-api-key-here
```

Supported values for `LLM_PROVIDER`: `mock`, `gemini`, `openai`, `groq`

When `LLM_PROVIDER=mock` (default), the system uses offline grounded synthesis from retrieved ICAR evidence chunks without calling any external LLM.

---

## Hallucination Control

The system is architecturally designed to prevent hallucination:

- Advisory text is generated **only** from retrieved ICAR/authorized document chunks.
- The LLM prompt explicitly prohibits inventing chemical doses, fertilizer quantities, or disease treatment schedules not found in retrieved evidence.
- If evidence is insufficient, the system explicitly states that rather than generating ungrounded information.
- Every recommendation cites the source document, institution, and page number.

---

## Important Notes

- Agricultural facts are **never hardcoded** in Python code.
- The knowledge base must contain only **genuine, authorized** agricultural source documents.
- Synthetic or fabricated PDFs must not be placed in `data/knowledge_base/`.
- The `data/chroma/` directory and `data/interactions.db` are created automatically at runtime.
