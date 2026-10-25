# AgriIntel AI - Project Plan

## Project Objective

Build a domain-specific agricultural advisory system that combines:
- Farmer queries
- Crop information
- Location
- Agricultural knowledge retrieval
- Weather information
- LLM-based advisory
- Structured interaction dataset

## Initial Crops

1. Rice
2. Cotton
3. Maize

## System Pipeline

Farmer Query
    ↓
Query Understanding
    ↓
Crop + Location Extraction
    ↓
Agricultural Knowledge Retrieval (RAG)
    ↓
Weather API
    ↓
Context Integration
    ↓
LLM
    ↓
Agricultural Advisory
    ↓
Interaction Dataset

## Development Phases

### Phase 1 - Foundation and Knowledge Base
Weeks 1-3

- Project architecture
- Agricultural document collection
- PDF/text extraction
- Cleaning
- Chunking
- Metadata
- Embeddings
- Vector database
- Initial retrieval

### Phase 2 - RAG + Weather
Weeks 4-7

- Query understanding
- Crop detection
- Location handling
- RAG retrieval
- Weather API
- Context integration

### Phase 3 - LLM Advisory + Dataset
Weeks 8-11

- LLM integration
- Grounded response generation
- Hallucination prevention
- Interaction dataset
- Database storage

### Phase 4 - Frontend + Evaluation
Weeks 12-16

- Minimal frontend
- Backend/frontend integration
- Testing
- Retrieval evaluation
- Advisory evaluation
- End-to-end testing

### Phase 5 - Finalization
Weeks 17-20

- Improvements
- Documentation
- Results
- Screenshots
- Report
- Presentation
- Viva preparation

## Team Responsibilities

### Member 1 - Lead / AI Backend
- Architecture
- FastAPI backend
- RAG pipeline
- LLM integration
- System integration

### Member 2 - Knowledge Base
- Agricultural documents
- Source verification
- PDF processing
- Metadata
- Rice/Cotton/Maize knowledge base

### Member 3 - Weather + Dataset
- Weather API
- Location/weather handling
- Interaction dataset
- Database storage

### Member 4 - Frontend + Testing
- Frontend
- API integration
- Test cases
- Evaluation
- Documentation support

## Current Status

Phase 1 - IN PROGRESS

- [x] Python environment
- [x] Virtual environment
- [x] FastAPI skeleton
- [x] Health endpoint
- [x] Swagger documentation
- [ ] Agricultural documents
- [ ] Document ingestion
- [ ] Chunking
- [ ] Embeddings
- [ ] Vector database
- [ ] Retrieval

## Important Principles

- Do not hardcode agricultural facts.
- Use authoritative agricultural sources.
- Knowledge Base and Interaction Dataset are separate.
- Do not generate an advisory without sufficient supporting evidence.
- Prefer simple, understandable technologies.
- Every team member must understand their component.