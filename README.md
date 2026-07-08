# AI Knowledge Inbox

A minimal, single-user "knowledge inbox": save notes and URLs, then ask questions
that are answered from your own saved content using a Retrieval-Augmented
Generation (RAG) pipeline. Answers come back with the source snippets they were
grounded in, so you can verify them.

- **Backend:** Python + FastAPI, SQLite, Google Gemini (embeddings + chat)
- **Frontend:** React + Vite + TypeScript + Tailwind
- **Vector search:** brute-force cosine similarity over embeddings loaded into memory,
  persisted in SQLite

---

## Quick start

You need **Python 3.11+**, **Node 18+**, and a **free Gemini API key**
(get one at https://aistudio.google.com/apikey).

### 1. Backend

```bash
cd backend
python -m venv venv
# Windows:  venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # then edit .env and set GEMINI_API_KEY
uvicorn app.main:app --reload
```

Backend runs at `http://localhost:8000`. Interactive API docs at
`http://localhost:8000/docs`. Health check at `http://localhost:8000/health`.

> Dependencies are pinned to versions with prebuilt wheels for Python 3.11–3.14,
> so `pip install` needs no compiler.

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env        # optional; defaults to http://localhost:8000
npm run dev
```

Frontend runs at `http://localhost:5173`.

---

## How it works

```
                 ┌─────────────┐        ┌──────────────────────────────┐
  POST /ingest → │  ingest_    │  note  │ normalize text               │
  (note | url)   │  pipeline   │───────▶│ or fetch URL + extract text  │
                 └─────┬───────┘        └──────────────┬───────────────┘
                       │                               │
                       │              chunk (paragraph-aware, overlap)
                       │                               │
                       │              embed chunks (Gemini)
                       │                               │
                       ▼                               ▼
                 ┌───────────────┐          ┌─────────────────────┐
                 │ SQLite        │          │ in-memory vector    │
                 │ items+chunks  │◀────────▶│ index (cosine)      │
                 └───────────────┘          └─────────────────────┘
                       ▲                               ▲
  POST /query ─────────┘   embed question → top-k cosine → build context
  (question)               → LLM answer + cited sources ─┘
```

The vector index is the durable SQLite `chunks` table plus an in-memory numpy
matrix rebuilt on startup. Ingest writes to both; query reads from memory.

---

## API

Base URL: `http://localhost:8000`

### `POST /ingest` → `201 Created`

Add a note or a URL. Fetches + extracts URL content server-side, then chunks,
embeds, and stores it.

```jsonc
// note
{ "type": "note", "content": "Text of the note", "title": "optional" }
// url
{ "type": "url", "url": "https://example.com/article", "title": "optional" }
```

Response:

```json
{
  "id": 1,
  "type": "url",
  "title": "Example Article",
  "source_url": "https://example.com/article",
  "created_at": "2026-07-08T12:00:00+00:00",
  "chunk_count": 7
}
```

### `GET /items` → `200 OK`

List saved items (newest first) with a snippet and chunk count. Raw content is
not returned in the list to keep the payload small.

### `POST /query` → `200 OK`

```json
{ "question": "What did the article say about pricing?" }
```

Response:

```json
{
  "answer": "The article says pricing starts at $10/mo … (Source 1).",
  "sources": [
    {
      "item_id": 1,
      "title": "Example Article",
      "source_url": "https://example.com/article",
      "chunk_text": "Pricing starts at $10/mo for the starter tier…",
      "score": 0.83
    }
  ]
}
```

### Error model

Errors return `{ "detail": "<message>" }` with a status code chosen for the cause:

| Status | When |
| ------ | ---- |
| `422`  | Invalid request body (missing/empty `content`/`url`/`question`, bad URL scheme) |
| `502`  | Upstream failure: URL fetch failed/timed out, or Gemini embeddings/chat failed |
| `404`  | Item not found |
| `500`  | Unexpected server error |

Asking a question with an empty knowledge base is **not** an error — it returns
`200` with an answer telling you to add content first.

---

## Design decisions & tradeoffs

### Chunking: paragraph-aware packing with overlap

Text is split on blank lines into paragraphs (natural semantic units), then
paragraphs are packed into chunks up to ~1000 characters. Each new chunk repeats
the trailing ~150 characters of the previous one (**overlap**), so a fact that
straddles a boundary still has surrounding context on both sides. A single
paragraph larger than the budget is hard-split on a fixed window.

- **Why character-based, not token-based:** simpler, no tokenizer dependency, and
  "good enough" at this scale. Characters are a rough proxy for tokens (~4 chars/token).
- **Cost of the shortcut:** chunk boundaries can land mid-sentence for hard-split
  paragraphs, and character budgets don't map exactly to the embedding model's token
  limit. For production I'd switch to token-aware, sentence-boundary-respecting chunking
  (e.g. tiktoken) and tune size/overlap against a retrieval eval set.

### Vector store: SQLite + in-memory brute-force cosine

Embeddings are stored as `float32` blobs in the SQLite `chunks` table. On startup
they're loaded into a normalized numpy matrix; each query is a single matrix-vector
product (`O(n)` over all chunks).

- **Why:** a single-user inbox has thousands of chunks at most. Brute force is exact
  (no recall loss from approximate indexes), needs zero extra infrastructure, and is a
  few lines of numpy. SQLite gives durability for free.
- **Cost:** the whole index lives in RAM and is rebuilt on every restart; search is
  linear in chunk count.

### Embeddings + LLM: Google Gemini, behind a thin wrapper

`gemini-embedding-001` for embeddings, `gemini-2.5-flash` for answers — both on
Gemini's free tier, so the app runs at zero cost. Gemini embeddings are asymmetric:
chunks are embedded with `task_type=RETRIEVAL_DOCUMENT` and questions with
`RETRIEVAL_QUERY`, which improves retrieval over embedding both the same way. Both
are isolated in `services/embeddings.py` and `services/rag.py` over a single
`gemini_client.py`, so swapping providers (Gemini was itself dropped in for OpenAI
in one wrapper file) is a contained change, not a rewrite.

### Grounded answers

The LLM is instructed to answer **only** from the retrieved context and to say when
the context is insufficient rather than hallucinate. Retrieved chunks are returned to
the client as `sources` (with similarity scores) so answers are auditable.

---

## What breaks at scale

| Concern | Breaks when | Fix |
| ------- | ----------- | --- |
| **Vector search** | Tens of thousands+ of chunks — linear scan gets slow, RAM grows | Move to pgvector / Qdrant / a proper ANN index (HNSW) |
| **In-memory index** | Multiple backend processes/replicas — each holds its own copy, and it rebuilds on restart | Externalize the index to a shared vector DB |
| **SQLite writes** | Concurrent writers — SQLite serializes writes | Postgres |
| **Synchronous ingest** | Large pages / many chunks block the request | Background job queue (Celery/RQ/arq); return `202 Accepted` + status |
| **Ingest atomicity** | Item is committed before its chunks in a separate transaction — a crash mid-ingest can orphan an item | Single transaction across item + chunks, or a cleanup sweep |
| **No dedup** | Same URL ingested twice → duplicate chunks | Content hashing + upsert |
| **URL fetch** | JS-rendered pages, paywalls, PDFs | Headless browser (Playwright) + per-type extractors |

## What I'd add for production

- **Auth + multi-tenancy** (out of scope here — single user by design)
- **Async ingestion** with a job queue and status polling
- **Retries + backoff** on Gemini calls; circuit breaker on repeated failures
- **Rate limiting** and request size caps on ingest
- **Retrieval evals** (golden question/answer set) to tune chunking, `top_k`, and prompts
- **Observability:** request tracing, token/cost metrics, latency histograms

---

## Debuggability

- **Structured logging** — one logger per module, key=value events
  (`item_ingested item_id=1 type=url chunks=7`, `query_answered … sources=5`,
  `url_fetched url=… chars=…`). Noisy httpx/google-genai loggers are quieted.
- **Domain errors map to HTTP status codes** via a small exception hierarchy
  (`app/errors.py`) and a single FastAPI exception handler, so the client always
  gets a clean `{ "detail": ... }`.
- **Input validation** lives in Pydantic schemas (`app/schemas.py`) — the wrong
  shape is rejected with a clear `422` before any work happens.

---

## Project structure

```
backend/
  app/
    main.py              # app wiring, CORS, lifespan (init DB + load index), error handler
    config.py            # env-driven settings (models, chunk sizes, top_k)
    db.py                # SQLite schema + connection helper
    schemas.py           # Pydantic request/response models
    errors.py            # domain exceptions → HTTP status codes
    logging_config.py    # structured logging setup
    repository.py        # data access for items + chunks (no business logic)
    routers/
      items.py           # POST /ingest, GET /items
      query.py           # POST /query
    services/
      ingestion.py       # fetch URL + extract text; normalize notes
      ingest_pipeline.py # orchestrates normalize → chunk → embed → persist
      chunking.py        # chunking strategy
      embeddings.py      # Gemini embeddings wrapper (doc vs query task types)
      gemini_client.py   # Gemini client singleton
      vector_store.py    # in-memory cosine index over SQLite embeddings
      rag.py             # retrieve → build context → LLM answer + sources
  tests/                 # offline unit tests (chunking, vector search)

frontend/
  src/
    api.ts               # single API client (error normalization, base URL)
    types.ts             # shared types mirroring backend schemas
    App.tsx              # layout + shared item state
    components/
      AddItemForm.tsx    # add note / URL
      ItemList.tsx       # list saved items
      AskPanel.tsx       # question box + request state
      AnswerView.tsx     # answer + cited source snippets
```

---

## Tests

Offline unit tests (no network, no API key needed) cover the chunking strategy and
the cosine ranking:

```bash
cd backend
pip install pytest
pytest -q
```
