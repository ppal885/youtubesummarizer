# YouTube Video Copilot

**Transcript-grounded** summaries and Q&A for YouTube: FastAPI backend, optional React UI, LangGraph copilot workflow, hybrid retrieval (lexical + optional pgvector), and a small **learning assistant** (notes, quiz, flashcards, markdown export).

> **Naming:** the Python package lives under the directory `youtube_summarizer/` (historical). The product and API title use **YouTube Video Copilot** (`APP_NAME`).

---

## Contents

- [Overview](#overview)
- [Tech stack](#tech-stack)
- [Repository layout](#repository-layout--naming-conventions)
- [Quick start](#quick-start)
- [Architecture summary](#architecture-summary)
- [Screenshots (placeholders)](#screenshots-placeholders)
- [API reference](#api-reference)
- [API examples (`curl`)](#api-examples-curl)
- [Configuration](#configuration)
- [Ask workflow (LangGraph)](#ask-workflow-langgraph--copilot)
- [Learning assistant](#learning-assistant)
- [Retrieval (hybrid + Postgres)](#retrieval-hybrid--postgres)
- [Frontend](#frontend-vite--react)
- [Evaluation CLI](#evaluation-cli)
- [Engineering decisions](#engineering-decisions)
- [Tradeoffs](#tradeoffs)
- [Future roadmap](#future-roadmap)
- [Tests & errors](#tests--error-behavior)

---

## Overview

| Goal | How |
|------|-----|
| Accurate summaries | Chunk captions → LLM per chunk → merge; optional in-memory cache by `(video_id, summary_type)`. |
| Grounded Q&A | Retrieve top chunks → compose answer from **CONTEXT only** → **verifier** + lexical confidence + citations. |
| Study aids | Same chunking as summarize; time-labeled transcript prompts for notes / quiz / cards. |
| Demos without keys | `LLM_PROVIDER=mock`, `RETRIEVER_PROVIDER=mock`. |

OpenAPI: **`/docs`** after starting the server.

---

## Tech stack

- **Backend:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy, LangGraph  
- **LLM:** `LLMService` ABC → `mock` / OpenAI-compatible (`openai` SDK) / Anthropic  
- **DB:** SQLite by default; PostgreSQL + **pgvector** for embedding retrieval  
- **UI:** Vite + React + TypeScript (streaming chat over `/api/v1/ask/stream`)

---

## Repository layout & naming conventions

```
youtube_summarizer/
├── app/
│   ├── main.py              # FastAPI app factory
│   ├── config.py            # Pydantic Settings (env)
│   ├── routers/             # HTTP: thin handlers, map exceptions → status codes
│   ├── services/            # Orchestration: summary, qa, learning, export, streaming
│   ├── workflows/           # LangGraph: ask_graph, ask_retrieval_phase (stream prelude)
│   ├── copilot/             # Analyst, retrieval rerank, composer, verifier (+ contracts)
│   ├── repositories/      # Transcript chunks, summaries persistence
│   ├── models/              # request/response DTOs, retrieval types, stream events
│   ├── evaluation/          # Offline metrics CLI
│   └── ...
├── docs/
│   ├── ARCHITECTURE.md      # Diagrams + pipeline depth
│   └── screenshots/         # Demo image placeholders (see docs/screenshots/README.md)
├── frontend/                # Vite React client
├── tests/
└── requirements.txt
```

**Conventions**

| Area | Pattern |
|------|---------|
| HTTP models | `*Request` / `*Response` in `app/models/request_models.py` & `response_models.py` |
| LLM JSON shapes | `*Payload` in `app/services/llm/schemas.py` |
| Graph state | `CopilotAskState` (typed, `extra="forbid"`) |
| Routers | One module per area: `summarize`, `ask`, `learning`, `compare`, `config_public` |
| Exceptions | Domain errors in `app/exceptions.py`; routers translate to HTTP |

---

## Quick start

```bash
cd youtube_summarizer
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1
# Unix:    source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env   # or cp on Unix; set LLM_PROVIDER=mock for offline
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

- API: [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs)  
- UI (optional): `cd frontend && npm install && npm run dev` → [http://localhost:5174](http://localhost:5174) (proxies `/api` to **8001**)

---

## Architecture summary

1. **Ingest:** resolve `video_id`, fetch captions (`youtube-transcript-api`), normalize text.  
2. **Chunk:** sentence-aware splits with char or token caps (`chunk_service`).  
3. **Summarize:** map-reduce LLM over chunks → merge → suggested questions, chapters, key moments → persist `summary_results`.  
4. **Ask:** LangGraph nodes validate → chunk → **Transcript Analyst** (themes, non-evidence) → persist chunks → **hybrid retrieve** → **Retrieval rerank** → **Answer Composer** (JSON QA) → **Verifier** → `AskResponse` with `sources` + `confidence`.  
5. **Stream:** same retrieval prelude (`ask_retrieval_phase`), then plain-text token stream + verify on full string → SSE `done` with final answer.  
6. **Learning:** shared labeled transcript builder → separate LLM JSON payloads per endpoint.

**Full diagrams (Mermaid) and scaling notes:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Screenshots (placeholders)

Drop images under `docs/screenshots/` and uncomment or add rows below.

| Preview | File (add when ready) |
|---------|------------------------|
| Summarize + video | `docs/screenshots/01-home-summarize.png` |
| Summary + suggested questions | `docs/screenshots/02-summary-panel.png` |
| Ask / streaming chat | `docs/screenshots/03-ask-streaming.png` |
| Sources + confidence | `docs/screenshots/04-sources-confidence.png` |

Checklist and naming ideas: [docs/screenshots/README.md](docs/screenshots/README.md).

Example (when files exist):

```markdown
![Summarize](docs/screenshots/01-home-summarize.png)
```

---

## API reference

Base path: **`/api/v1`**.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/summarize` | Structured summary + bullets + key moments + suggested questions + chapters; persists row. |
| `GET` | `/summaries` | Recent stored summaries (`?limit=`). |
| `POST` | `/ask` | Transcript Q&A JSON (`answer`, `sources`, `confidence`). |
| `POST` | `/ask/stream` | SSE: `delta` tokens then `done` with final grounded answer + metadata. |
| `POST` | `/compare` | Two URLs → summaries → LLM comparison. |
| `GET` | `/config` | Public LLM config for UI (no secrets). |
| `POST` | `/notes` | Learning: concise + detailed notes + glossary. |
| `POST` | `/quiz` | Learning: MCQ with `answer` text + explanation. |
| `POST` | `/flashcards` | Learning: front/back + optional timestamp. |
| `POST` | `/export-notes` | Markdown bundle (brief summarize + notes + quiz + cards). |

---

## API examples (`curl`)

Replace the sample URL with any **captioned** public video. Default server: **`127.0.0.1:8001`**.

**Summarize**

```bash
curl -s -X POST "http://127.0.0.1:8001/api/v1/summarize" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ","summary_type":"brief","language":"en"}'
```

**List recent summaries**

```bash
curl -s "http://127.0.0.1:8001/api/v1/summaries?limit=5"
```

**Ask (JSON)**

```bash
curl -s -X POST "http://127.0.0.1:8001/api/v1/ask" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ","question":"What is the video about?","language":"en"}'
```

Example shape:

```json
{
  "answer": "…",
  "confidence": 0.82,
  "sources": [
    { "start_time": 66.0, "formatted_time": "01:06", "text": "…" }
  ]
}
```

**Ask (stream)** — consume with `curl -N` or your UI; each line is `data: {JSON}`.

```bash
curl -N -X POST "http://127.0.0.1:8001/api/v1/ask/stream" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ","question":"What is the video about?","language":"en"}'
```

**Compare two videos**

```bash
curl -s -X POST "http://127.0.0.1:8001/api/v1/compare" \
  -H "Content-Type: application/json" \
  -d '{"url_1":"https://www.youtube.com/watch?v=VIDEO_A","url_2":"https://www.youtube.com/watch?v=VIDEO_B","summary_type":"brief","language":"en"}'
```

**Public config**

```bash
curl -s "http://127.0.0.1:8001/api/v1/config"
```

**Learning**

```bash
curl -s -X POST "http://127.0.0.1:8001/api/v1/notes" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ","language":"en"}'
# Swap path: /quiz, /flashcards
```

**Export markdown**

```bash
curl -s -X POST "http://127.0.0.1:8001/api/v1/export-notes" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ","export_type":"markdown","language":"en"}'
```

---

## Configuration

Copy **`.env.example`** → **`.env`**.

### LLM

| Variable | Description |
|----------|-------------|
| `APP_NAME` | Shown in OpenAPI title (default: YouTube Video Copilot). |
| `LLM_PROVIDER` | `mock` \| `openai` \| `anthropic` |
| `LLM_API_KEY` | Required for hosted OpenAI/Anthropic; often optional for local OpenAI-compatible gateways. |
| `LLM_MODEL` | Model id for the active provider. |
| `LLM_BASE_URL` | OpenAI-compatible only; empty → `https://api.openai.com/v1`. |
| `LLM_TIMEOUT_SECONDS` | Default `120`. |
| `LLM_JSON_RESPONSE_FORMAT` | OpenAI-compatible: set `false` if `json_object` mode breaks your local server. |

### Chunking

| Variable | Description |
|----------|-------------|
| `MAX_CHUNK_CHARS` / `CHUNK_OVERLAP_CHARS` | Character mode (overlap &lt; max). |
| `CHUNK_USE_TOKENS` | `true` → `tiktoken` caps (`MAX_CHUNK_TOKENS`, `CHUNK_OVERLAP_TOKENS`). |

### Database & retrieval

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Default SQLite `sqlite:///./summaries.db`; use Postgres for `RETRIEVER_PROVIDER=embedding`. |
| `RETRIEVER_PROVIDER` | `mock` (lexical/BM25-style) or `embedding` (pgvector + hybrid). |
| `QA_RETRIEVAL_POOL` | Wide retrieval pool before compression (legacy: **`QA_TOP_K`**). Default **10**. |
| `QA_CONTEXT_COMPRESS_TO` | Target **3–5** compressed blocks for the answer LLM (default **4**). Must be ≤ pool. |
| `QA_CONTEXT_COMPRESSION` | **`heuristic`** (merge/rank-local) or **`llm`** (one JSON compression call; falls back on error). |
| `EMBEDDING_PROVIDER` / `EMBEDDING_MODEL` / `EMBEDDING_API_KEY` / `EMBEDDING_DIMENSIONS` | Embedding path (see `.env.example`). |
| `RETRIEVAL_HYBRID_ALPHA` / `RETRIEVAL_HYBRID_BETA` | Semantic vs keyword weights (must not both be zero). |

### CORS

| Variable | Description |
|----------|-------------|
| `CORS_ORIGINS` | Comma-separated origins for browser clients (Vite ports included by default). |

Misconfiguration returns **503**/**501** with short messages where applicable. **`GET /api/v1/config`** exposes safe LLM fields for the UI.

---

## Ask workflow (LangGraph + copilot)

**Summarize** stays a **linear** `SummaryService` pipeline. **Ask** uses a **compiled LangGraph** (`app/workflows/ask_graph.py`) with typed `CopilotAskState` and deps injected via `RunnableConfig["configurable"]["deps"]` (`AskGraphDeps`).

Agents under `app/copilot/` are **plain classes** + **Pydantic contracts** (`contracts.py`). They **fail safe** so the graph can still return an **`AskResponse`**.

| Agent | Role |
|--------|------|
| **Transcript Analyst** | Coarse time-banded themes (**not** evidence). |
| **Retrieval** | Re-ranks hybrid hits using theme overlap as a hint. |
| **Answer Composer** | `LLMService.answer_question` with CONTEXT + labeled orientation. |
| **Verifier** | Lexical grounding (`qa_grounding`), confidence, “Not mentioned in video” fallback. |

**Graph nodes:** `validate_input` → `extract_video_id` → `fetch_transcript` → `clean_transcript` → `chunk_transcript` → (`transcript_analyst` → `retrieve_context` if chunks exist) → `answer_question` → `validate_grounding` → `format_response`. Empty chunks or retrieval → skip LLM, still `format_response`.

Dependency: **`langgraph`**.

---

## Learning assistant

| Path | Returns (high level) |
|------|----------------------|
| `/notes` | `concise_notes`, `detailed_notes`, `glossary_terms[]` |
| `/quiz` | MCQ: `options[4]`, `answer` (correct option text), `explanation` |
| `/flashcards` | `front`, `back`, optional `timestamp_seconds` / `formatted_time` |
| `/export-notes` | `markdown_content`, `suggested_filename` |

Implementation: `learning_transcript.py` (chunk + time labels), `learning_prompting.py`, `learning_service.py`.

---

## Retrieval (hybrid + Postgres)

**Formula:** `final_score = α × semantic_score + β × keyword_score`

- **Semantic:** pgvector cosine → mapped to `[0,1]`; **mock** retriever has no vectors (semantic term **0** unless you set **α=0**).  
- **Keyword:** BM25-style over **per-video** corpus, max-normalized.

**Postgres + pgvector:** enable extension, set `DATABASE_URL`, `RETRIEVER_PROVIDER=embedding`. Startup runs `CREATE EXTENSION IF NOT EXISTS vector` where privileges allow. **No Alembic** in this MVP (`create_all` only).

---

## Frontend (Vite + React)

- **Ports:** API **8001**, Vite **5174** (see `frontend/.env.example`).  
- **Features:** embedded player, summary panel, suggested questions, **streaming** transcript Q&A (`postAskStream`).  
- **Production:** `npm run build`, set `VITE_API_BASE` to your API origin.

---

## Evaluation CLI

Heuristic metrics (no gold labels). Run **`python -m app.evaluation.cli --help`** (`--url`, `--questions-file`, `-o`, …).

| Output (run + per-question) | Meaning |
|-----------------------------|---------|
| `summary_faithfulness_score` | Share of summary+bullet tokens found in full transcript. |
| `answer_grounding_score` | Verifier `confidence` (same idea as `/ask`). |
| `retrieval_relevance_score` | Question ↔ retrieved passage text overlap. |
| `chunk_coverage_score` | Distinct retrieved chunk indices ÷ total chunks. |
| `retrieved_chunk_count` / `answer_has_sources` | Retrieval breadth; citations present. |
| `average_latency_ms` | Mean over 1× summarize + N× ask. |

Code: **`app/evaluation/`**; models: **`app/evaluation/models.py`**.

---

## Engineering decisions

| Decision | Rationale |
|----------|-----------|
| **LangGraph for Ask only** | Summarize is a straight pipeline; Ask benefits from explicit branches (no retrieval → no LLM) and typed state for interviews and debugging. |
| **Copilot as plain services** | Avoids opaque “agent” frameworks; contracts are testable Pydantic models. |
| **JSON for non-stream QA, plain text for stream** | JSON keeps structured `answer` parsing reliable; streaming uses a parallel system prompt (`QA_STREAM_*`) then the same verifier on the full string. |
| **Retriever + repository split** | Persistence (chunk rows, embeddings) stays in SQLAlchemy; ranking logic stays in `ChunkRetriever` implementations. |
| **In-memory summary cache** | Fast repeat demos for the same `(video_id, summary_type)`; language intentionally omitted from key (documented). |
| **Pydantic Settings** | Single source of truth for env with validation (e.g. α+β not both zero). |

---

## Tradeoffs

| Choice | Upside | Downside |
|--------|--------|----------|
| **SQLite default** | Zero setup for demos | Poor concurrent writers; not for heavy embedding traffic. |
| **No Alembic** | Fast iteration | Manual schema drift handling when changing models. |
| **Lexical verifier** | Cheap, deterministic guardrails | Not semantic entailment; can disagree with “obvious” paraphrases. |
| **Re-fetch transcript per Ask** | Always matches current chunk settings | Extra YouTube API traffic vs a shared session cache. |
| **SSE errors as `data:` events** | Simple client parsing | HTTP 200 on stream; clients must handle `type:error`. |
| **Export-notes runs full summarize + learning** | One-shot bundle | High latency/cost vs single endpoint. |

---

## Future roadmap

| Track | Ideas |
|-------|--------|
| **Product** | Auth, saved sessions, share links, Notion/Obsidian export, thumbnail timelines. |
| **Quality** | Cross-encoder rerank, NLI or LLM-judge eval, golden Q&A sets in CI. |
| **Ops** | OpenTelemetry, Prometheus, request IDs across summarize + ask. |
| **Infra** | Redis for summary + caption cache, job queue for long exports, read replicas for Postgres. |
| **UI** | Recent summaries view, dark mode, mobile layout. |

---

## Tests & error behavior

```bash
pytest
```

| Condition | Typical HTTP |
|-----------|----------------|
| Bad YouTube URL | `400` |
| No / bad captions | `404` |
| Unknown provider | `501` |
| Missing API key / DB setup | `503` |
| LLM / embedding failure | `502` |
| DB failure after LLM success (summarize save) | `500` |

**Mock LLM:** no outbound calls; deterministic for CI.

---

## Additional documentation

- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — Mermaid component + sequence diagrams, pipelines, caching, observability, scaling.  
- **[docs/screenshots/README.md](docs/screenshots/README.md)** — Demo capture checklist.
