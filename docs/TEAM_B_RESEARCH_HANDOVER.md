# AgriIntel AI â€” Team B Research Paper Handover

**Target Audience:** Pallapu Akhila & Laaibah Tazaeen (Team B)
**Project Phase:** Pre-Exam Freeze (Nov 8, 2026) $\to$ Drafting Track (Nov 8 â€“ Dec 10, 2026)
**Base Architecture:** `integration/audit-consolidated`
**Base Paper:** *CottonBot: An AI-driven cotton farming assistant and irrigation advisor using LLM-RAG and agentic AI tools* (Kandamali et al., *Smart Agricultural Technology*, 2024)

---

## 1. Project Title, Scope & Core Objectives

### Formal Research Title
> **"AgriIntel AI: Smart Agricultural Advisory and Dataset Generation from Farmer Queries and Weather Intelligence"**

### Project Overview & Objectives
AgriIntel AI is a retrieval-augmented agricultural advisory and dataset curation system designed for Indian smallholder farming contexts. Built on authentic publications from the Indian Council of Agricultural Research (ICAR) and affiliated national institutes, it provides reliable, evidence-grounded agronomic recommendations across **five major crops**:
1. **Rice (Paddy)** â€” ICAR-NRRI
2. **Cotton** â€” ICAR-CICR
3. **Maize (Corn)** â€” ICAR-IIMR
4. **Groundnut (Peanut)** â€” ICAR-DGR
5. **Soybean** â€” ICAR-IISR

### Primary Research Objectives
1. **Cross-Crop Hallucination & Contamination Defense:** Prevent cross-crop treatment errors (e.g., misapplying cotton bollworm pesticides to groundnut) via deterministic query understanding, crop conflict detection, and chunk-level crop isolation.
2. **Multi-Aspect Intent Grounding:** Enforce evidence sufficiency gates that require authentic ICAR literature to verify both diagnostic symptoms and curative measures before recommending chemical interventions.
3. **Dynamic Environmental Grounding:** Synthesize static agronomic best practices with dynamic real-time weather forecasts (temperature, humidity, precipitation, wind speed) from the Open-Meteo API.
4. **Automated Agricultural Interaction Curation:** Automatically log real-time farmer queries, extracted metadata, weather context, and grounded responses into structured SQLite, JSONL, and CSV datasets for training and benchmarking domain-specific Small Language Models (SLMs).

---

## 2. Actual Technology Stack

When describing the implementation in the paper, strictly adhere to the actual software stack:

| Component | Technology / Library | Role in AgriIntel AI |
|---|---|---|
| **Backend Framework** | Python 3.13, FastAPI 0.115, Uvicorn | High-performance asynchronous REST API |
| **Data Validation** | Pydantic v2, `pydantic-settings` | Strict schema validation for queries, advisories, and weather |
| **Document Ingestion** | PyMuPDF (Fitz $\ge 1.28.2$) | PDF text extraction, glyph/ligature normalization, page provenance |
| **Chunking Engine** | Custom Sentence-Boundary Chunker | 1,000-char chunks, 100-char overlap, sentence boundary adherence, crop filtering |
| **Embedding Model** | `sentence-transformers/all-MiniLM-L6-v2` | 384-dimensional dense semantic query & passage vectors |
| **Vector Database** | ChromaDB ($\ge 1.5.9$, Persistent) | Local vector storage with HNSW index and Cosine Distance metric |
| **Weather Engine** | Open-Meteo REST API (`httpx`) | Free, keyless geocoding and 3-day meteorological forecasts |
| **LLM Synthesis Layer** | Gemini 1.5 Flash / GPT-4o-mini / Llama 3.1 / Offline Synthesizer | Multi-provider synthesis with offline deterministic fallback |
| **Interaction Dataset** | SQLite 3 | Structured interaction logging with JSONL & CSV export endpoints |
| **Frontend UI** | React 19, Vite 8, Tailwind/Vanilla CSS | Responsive farmer query interface with grounding status badges |

---

## 3. CottonBot Methodology & Detailed Comparison

The base paper for this project is:
*Deus F. Kandamali, Wesley Porter, Erin Porter, Alex McLemore, and Glen C. Rains (2024). "CottonBot: An AI-driven cotton farming assistant and irrigation advisor using LLM-RAG and agentic AI tools", Smart Agricultural Technology.*

### Detailed Architectural Comparison Table

| Dimension | CottonBot (Kandamali et al., 2024) | AgriIntel AI (Our System) | Scientific Distinction |
|---|---|---|---|
| **Crop Scope** | **Single Crop:** Cotton only | **Multi-Crop:** Rice, Cotton, Maize, Groundnut, Soybean | AgriIntel addresses cross-crop contamination, routing, and conflict disambiguation. |
| **Knowledge Base** | US cotton extension leaflets | Official Indian ICAR institute publications | Tailored for Indian agro-climatic zones and ICAR package of practices. |
| **Soil-Moisture Data** | **Physical IoT soil sensors** (in-field telemetry) | **Meteorological precipitation & weather data** | AgriIntel uses Open-Meteo rain/humidity rather than physical sensor probes. |
| **Predictive Modeling**| **LSTM neural network** for soil-moisture sequence forecasting | **Rule-grounded weather advisory synthesis** | AgriIntel does not use LSTM forecasting; do not claim LSTM in the paper. |
| **Irrigation Scheduling**| Agentic tool execution based on sensor thresholds | Dynamic weather grounding with ICAR growth-stage guidelines | Advises irrigation based on critical crop stages and 3-day rainfall forecasts. |
| **Hallucination Control**| Prompt engineering alone | **Two-Tier Grounding Gate:** Lexical intent gate + multi-aspect bipartite verification | Strict refusal if ICAR evidence is insufficient. |
| **Dataset Generation**| Unstructured interaction logs | **Structured Dataset Engine:** Automated logging & export to JSONL/CSV | Creates standardized datasets for fine-tuning agricultural SLMs. |

---

## 4. Implemented Technical Contributions Supported by Code

The following 4 contributions are **fully implemented in the code** and can be defended with technical rigor:

### Contribution 1: Multi-Crop Query Disambiguation and Conflict Protection
- In multi-crop advisory systems, users often ask ambiguous or contradictory questions (e.g. selecting "soybean" in a dropdown but asking "how to control blast in rice").
- AgriIntel implements a deterministic `QueryUnderstandingService` (`app/services/query_service.py`) that extracts crop names, growth stages, and intents.
- If the query-crop conflicts with the selected crop, the API halts execution and returns `HTTP 400 Bad Request` before calling retrieval or weather services, protecting against cross-crop chemical poisoning.

### Contribution 2: Multi-Aspect Intent Filtering with Candidate Expansion
- Standard RAG retrieves top-$k$ nearest neighbors solely by cosine similarity. In agriculture, general crop cultivation passages often outscore specific disease management passages.
- AgriIntel expands the candidate pool ($k \ge 10$, $k \ge 20$ for disease) and filters candidates using detected intent keywords (`app/services/retrieval_service.py`).
- For disease queries requiring both symptoms and management, the system verifies that retrieved passages cover both aspects before declaring the query grounded.

### Contribution 3: Two-Tier Anti-Hallucination Grounding Gate
- Large language models frequently hallucinate chemical dosages and pesticide schedules when context is sparse.
- AgriIntel introduces an architectural guard in `app/services/llm_service.py` (`_has_relevant_evidence`).
- If retrieved ICAR chunks do not contain verified vocabulary matching the query intent, the system triggers a verified refusal:
  > *"Reliable supporting information was not found in the curated ICAR knowledge base for this query."*
- Every recommendation is mapped to an explicit source document, publication year, and page number.

### Contribution 4: Automated Interaction Dataset Curation
- High-quality open-source agricultural datasets in Indian farming contexts are scarce.
- AgriIntel's `DatasetService` (`app/services/dataset_service.py`) logs every interaction into `interactions.db` with query text, detected crop, intent, growth stage, weather context, retrieved ICAR excerpts, and advisory text.
- Provides endpoints `GET /interactions/export?format=jsonl` and `GET /interactions/export?format=csv` with filtering by crop and evidence grounding status.

---

## 5. Proposed Research Gap & Paper Framing

When writing the paper, position the research gap as follows:

> **The Research Gap:**
> *"While existing agricultural conversational agents such as CottonBot demonstrate the potential of RAG for single-crop irrigation management, scaling AI advisory systems to multi-crop smallholder farming ecosystems introduces severe challenges: cross-crop agrochemical contamination, hallucination of fatal pesticide dosages, and the scarcity of authentic regional agronomic datasets. Current systems rely either on unconstrained LLMs prone to hallucination or mono-crop IoT frameworks requiring expensive sensor infrastructure unavailable to typical smallholder farmers."*

> **AgriIntel's Solution:**
> *"AgriIntel AI bridges this gap through an evidence-grounded, multi-crop RAG architecture that couples ICAR package-of-practices literature with Open-Meteo weather intelligence, a two-tier anti-hallucination verification gate, and an automated dataset generation pipeline that converts everyday farmer interactions into structured benchmark datasets."*

---

## 6. Paper Sections Team B Can Write Immediately (Pre-Dec 10)

Team B can write **over 65% of the research paper** during the exam period without waiting for experimental numbers:

### Section 1: Introduction (Ready to Write)
- Overview of Indian agriculture, smallholder farmer challenges, and extension service deficits.
- The danger of generic LLMs hallucinating chemical dosages without authentic literature backing.
- Introduction of AgriIntel AI and summary of the four key contributions.

### Section 2: Related Work (Ready to Write)
- Review of agricultural AI systems: AgriBERT, CropDoctor, FarmVibes, and CottonBot.
- Detailed comparison with CottonBot: single-crop vs. multi-crop; hardware IoT vs. open weather intelligence.
- Analysis of hallucination mitigation in RAG systems (prompting vs. programmatic verification gates).

### Section 3: Authoritative Knowledge Base & Document Curation (Ready to Write)
- Description of the 5 target crops: Rice, Cotton, Maize, Groundnut, Soybean.
- Curated ICAR institutes: ICAR-NRRI (Cuttack), ICAR-CICR (Nagpur), ICAR-IIMR (Ludhiana), ICAR-DGR (Junagadh), ICAR-IISR (Indore).
- Text extraction pipeline: PyMuPDF page-by-page processing, glyph/ligature normalization (`\u03d0` $\to$ `fl`), and metadata preservation (source ID, crop, page, title, year).

### Section 4: System Architecture & Methodology (Ready to Write)
- Detailed architectural diagram (see Section 5 of the Audit Report).
- **Mathematical Formulation:**
  - Query embedding: $\mathbf{q} = \text{Embed}(x)$ using `all-MiniLM-L6-v2`.
  - Candidate passage retrieval: $\mathcal{C}_k = \text{TopK}(\cos(\mathbf{q}, \mathbf{d}_i), \text{crop})$.
  - Intent filtering: $\mathcal{F}_{\text{intent}}(\mathcal{C}_k)$.
  - Multi-aspect grounding validation gate: $\mathcal{G}(x, \mathcal{C}_{\text{filtered}}) \in \{\text{True}, \text{False}\}$.
- Dynamic weather integration via Open-Meteo (temperature, precipitation, wind speed, 3-day forecast outlook).
- Interaction dataset engine schema (`interactions.db`, JSONL, CSV).

### Section 7: Conclusion & Future Work (Draftable Now)
- Summary of the multi-crop RAG architecture.
- Future work: fine-tuning domain SLMs (e.g. Llama-3-8B-Agri) using the curated interaction dataset, expanding to regional Indic languages (Telugu, Hindi, Marathi), and incorporating mobile speech interfaces.

---

## 7. Sections Requiring Team A's Post-Exam Experimental Results

Leave placeholders in the paper draft for these specific sections, which Team A will populate after December 10:

- **Section 5: Experimental Setup & Benchmark Evaluation:**
  - Description of the 20 benchmark queries (`data/evaluation/benchmark_queries.json`).
  - Table of Configurations: Baseline A (Dense), System B (+Crop), System C (+Crop +Intent), System D (Full Pipeline).
- **Section 6: Results and Discussion:**
  - LaTeX Table of $P@5$, $R@5$, MRR, and Latency across the 4 configurations.
  - Discussion of crop filter impact on precision (eliminating cross-crop false positives).
  - Qualitative Case Studies:
    - *Case 1:* Groundnut Tikka combined symptom and management grounding.
    - *Case 2:* Verified refusal of out-of-scope query (e.g. agricultural drone models).
    - *Case 3:* Crop conflict rejection (Soybean selected, Groundnut asked).

---

## 8. Critical Negative Constraints (Claims NOT to Make)

> [!CAUTION]
> **To prevent academic penalties or defense challenges, DO NOT make the following claims in the paper:**
> 1. **DO NOT claim IoT physical sensor integration:** AgriIntel does not have hardware soil moisture probes or microcontrollers in the codebase.
> 2. **DO NOT claim LSTM soil moisture forecasting:** CottonBot used an LSTM neural network; AgriIntel does **not** implement LSTM models. State clearly that AgriIntel uses real-time Open-Meteo precipitation and meteorological forecasts.
> 3. **DO NOT claim autonomous agentic irrigation control:** AgriIntel provides advisory recommendations; it does not trigger physical solenoid irrigation valves.
> 4. **DO NOT present synthetic test interactions as real farmer queries:** Explicitly label test queries as "curated benchmark queries based on ICAR package of practices."
