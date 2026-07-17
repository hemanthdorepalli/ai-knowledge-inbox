# AI Knowledge Inbox

A multi-user AI knowledge assistant: save notes, links, and documents, then ask
questions answered from **your own** content via a Retrieval-Augmented Generation
(RAG) pipeline. Every answer cites the source snippets it was grounded in, so it's
verifiable. Users can also connect **MCP servers** to give the assistant live tools
it can call while answering.

- **Backend:** Python + FastAPI, Supabase Postgres + pgvector, Google Gemini
- **Frontend:** React + Vite + TypeScript + Tailwind
- **Auth:** Google sign-in via Supabase Auth; per-user data isolated by Postgres RLS
- **Vector search:** pgvector with an HNSW index (cosine)

---

## Features

- **Ingest** plain notes, URLs (fetched + extracted server-side), and documents
  (PDF, DOCX, TXT, MD)
- **Ask questions** and get answers grounded in your saved content, with cited
  source snippets and similarity scores
- **Chat history** — persistent conversations, new chat, delete chat
- **MCP servers** — connect remote MCP servers; their tools become callable by the
  assistant during a chat answer (via Gemini function calling)
- **Token quotas** — a fixed per-user token budget covering both ingestion and chat,
  so a shared API key can't be run up

---

## Quick start

You need **Python 3.11+**, **Node 18+**, a free
[Gemini API key](https://aistudio.google.com/apikey), and a
[Supabase](https://supabase.com) project.

### 1. Database

In the Supabase dashboard → **SQL Editor**, run [`supabase/schema.sql`](supabase/schema.sql).
It enables pgvector and creates the tables, indexes, RLS policies, and the
`match_chunks` similarity-search function.

### 2. Google sign-in

1. **Google Cloud Console** → Credentials → create an **OAuth client ID** (Web).
   Set the authorized redirect URI to your Supabase callback:
   `https://<project>.supabase.co/auth/v1/callback`
2. **Supabase** → Authentication → Providers → **Google** → paste the Client ID +
   Secret → enable.
3. **Supabase** → Authentication → URL Configuration → add your app URL (e.g.
   `http://localhost:5173`) to **Site URL** and **Redirect URLs**.

### 3. Backend

```bash
cd backend
python -m venv venv
# Windows:  venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # then fill in the values below
uvicorn app.main:app --reload
```

Runs at `http://localhost:8000` — API docs at `/docs`, health at `/health`.

| Variable | What it is |
| --- | --- |
| `GEMINI_API_KEY` | Your Gemini API key |
| `SUPABASE_DB_URL` | Supabase → Settings → Database → **Session pooler** URI (URL-encode special characters in the password) |
| `SUPABASE_URL` / `SUPABASE_ANON_KEY` | Supabase → Settings → API |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins |
| `PUBLIC_HOST` | Optional. This backend's public hostname — auto-detected on Render; set only to override (see MCP notes) |

> **Use the Session pooler URL, not the direct connection.** The direct host
> (`db.<ref>.supabase.co`) resolves to IPv6-only, which many hosts (including
> Render) cannot reach.

> Dependencies are pinned to versions with prebuilt wheels for Python 3.11–3.14,
> so `pip install` needs no compiler.

### 4. Frontend

```bash
cd frontend
npm install
cp .env.example .env   # set VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY, VITE_API_BASE
npm run dev
```

Runs at `http://localhost:5173`.

---

## How it works

```
INGEST (note | url | document)
  POST /ingest, /ingest/document
        │
        ▼
  ingest_pipeline ──▶ get text: normalize note | fetch+extract URL | parse PDF/DOCX
        │
        ├──▶ chunking      (paragraph-aware packing, ~1000 chars, ~150 overlap)
        ├──▶ embeddings    (Gemini, batched ≤100, RETRIEVAL_DOCUMENT)
        └──▶ repository    (items + chunks, embedding vector(768)) ──▶ Postgres/pgvector


QUERY
  POST /query
        │
        ├──▶ embed question (RETRIEVAL_QUERY)
        ├──▶ match_chunks() ──▶ pgvector HNSW cosine search ──▶ top-k chunks
        ├──▶ MCP tools (if any connected) exposed to Gemini as function declarations
        │       └─▶ Gemini calls a tool ──▶ we execute it against the MCP server
        │           ──▶ feed the result back (as untrusted text) ──▶ repeat (capped)
        └──▶ answer + cited sources + tool calls ──▶ persisted to conversation history
```

---

## API

All endpoints except `/health` require `Authorization: Bearer <supabase-jwt>`.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Liveness check (open) |
| `POST` | `/ingest` | Add a note or URL |
| `POST` | `/ingest/document` | Upload a PDF/DOCX/TXT/MD (multipart) |
| `GET` | `/items` | List saved items (snippet + chunk count) |
| `POST` | `/query` | Ask a question → answer + sources + tool calls |
| `GET` | `/conversations` | List chat history |
| `GET` | `/conversations/{id}/messages` | Load a conversation's messages |
| `DELETE` | `/conversations/{id}` | Delete a conversation |
| `GET` | `/usage` | Token usage + limit |
| `GET`/`POST` | `/mcp-servers` | List / connect MCP servers |
| `PATCH`/`DELETE` | `/mcp-servers/{id}` | Enable-disable / remove |
| `POST` | `/mcp-servers/{id}/refresh` | Re-discover a server's tools |

**`POST /ingest`**

```jsonc
{ "type": "note", "content": "Text of the note", "title": "optional" }
{ "type": "url",  "url": "https://example.com/article", "title": "optional" }
```

**`POST /query`**

```json
{ "question": "What did the article say about pricing?", "conversation_id": null }
```

```json
{
  "answer": "Pricing starts at $10/mo (Source 1).",
  "sources": [{ "item_id": "…", "title": "Example Article", "chunk_text": "…", "score": 0.83 }],
  "conversation_id": "…",
  "tool_calls": []
}
```

### Error model

Errors return `{ "detail": "<message>" }` with a status chosen for the cause:

| Status | When |
| --- | --- |
| `401` | Missing/invalid/expired login token |
| `404` | Item or conversation not found |
| `422` | Invalid body, unsupported/oversized file, unsafe MCP URL |
| `429` | User's token quota exhausted |
| `502` | Upstream failure: URL fetch, Gemini, or MCP server |

Asking with an empty knowledge base is **not** an error — it returns `200` with an
answer saying to add content first.

---

## Design decisions & tradeoffs

### Chunking: paragraph-aware packing with overlap
Text is split on blank lines, then paragraphs are packed into ~1000-character chunks,
each repeating the previous chunk's trailing ~150 characters (**overlap**) so a fact
straddling a boundary keeps its context. Oversized paragraphs are hard-split.

- **Why character-based, not token-based:** no tokenizer dependency, good enough at
  this scale (~4 chars/token).
- **Cost:** boundaries can land mid-sentence, and character budgets don't map exactly
  to the model's token limit. In production: token-aware, sentence-respecting chunking
  tuned against a retrieval eval set.

### Vector search: Postgres + pgvector (HNSW)
Embeddings are stored in a `vector(768)` column with an HNSW cosine index; search runs
inside Postgres via the `match_chunks` function.

- **Why 768 dims:** Gemini can return 3072, but pgvector's HNSW index supports up to
  2000 — and 768 is cheaper and smaller while still strong.
- **Tradeoff:** HNSW is *approximate* — a small recall loss for a large speed gain.
  Exact brute-force search would be precise but linear in chunk count.

### Multi-tenancy: Postgres Row-Level Security
Every table carries a `user_id` with RLS policies (`auth.uid() = user_id`). Queries are
*also* scoped by `user_id` in the repository layer — defense in depth, so an app-layer
bug alone can't leak another user's data.

### Embeddings + LLM: Google Gemini, behind a thin wrapper
`gemini-embedding-001` + `gemini-2.5-flash`, both on the free tier. Gemini embeddings
are **asymmetric**: chunks use `RETRIEVAL_DOCUMENT`, questions use `RETRIEVAL_QUERY`,
which measurably improves retrieval. The provider is isolated to `gemini_client.py` +
two wrappers — this app was migrated from OpenAI to Gemini by changing only those.

Embedding calls are **batched to ≤100 per request** (Gemini's hard limit) and retry on
the per-minute rate limit; the per-**day** quota fails fast instead of retrying, since
waiting a minute can't recover a daily cap.

### Token quotas
Each user gets a fixed lifetime budget covering ingestion *and* chat. Chat usage is
metered exactly from Gemini's `usage_metadata`; embeddings report no usage data, so
they're estimated from character count (~4 chars/token) — deliberately a slight
overcount rather than undercount.

### MCP integration & security
Users connect **remote MCP servers**; their tools are exposed to Gemini as function
declarations, and the model can call them mid-answer.

- **Remote-only, never stdio.** Spawning a user-supplied process would be remote code
  execution on the backend.
- **SSRF-validated.** Every URL is resolved and rejected if it points at
  loopback/private/link-local/reserved ranges (e.g. cloud metadata at `169.254.169.254`).
- **We own the connection.** Gemini has a native `mcp_servers` passthrough, but using it
  would hand SSRF validation and execution to Google's infrastructure. We connect and
  execute ourselves instead.
- **Tool output is untrusted data** — fed back as text, never as instructions.
- **Round-trips are capped** (`MCP_MAX_TOOL_ROUNDS`) so a misbehaving server or model
  can't loop forever.

A **demo MCP server** is bundled at `/mcp-demo/mcp` (`get_current_time`, `roll_dice`) so
the feature is testable without standing up your own server.

> The MCP SDK enables DNS-rebinding protection, validating the `Host` header against an
> allowlist that defaults to **localhost only** — so a deployed instance rejects its own
> public URL with `421` unless that host is allowed. The app auto-detects its hostname
> (Render's `RENDER_EXTERNAL_HOSTNAME`) and allowlists it, keeping the protection on;
> **`PUBLIC_HOST`** overrides this if auto-detection isn't possible.

### Grounded answers
The model is instructed to answer only from the retrieved context and to say when it
can't, rather than hallucinate. Retrieved chunks and tool calls are returned to the
client so answers are auditable.

---

## What breaks at scale

| Concern | Breaks when | Fix |
| --- | --- | --- |
| **Synchronous ingest** | A large PDF (hundreds of chunks) can exceed a request timeout, especially with rate-limit backoff | Background job queue; return `202` + poll status |
| **Ingest atomicity** | The item is committed before its chunks — a crash mid-ingest orphans an item | One transaction across item + chunks, or a cleanup sweep |
| **No dedup** | The same URL/document ingested twice duplicates chunks | Content hashing + upsert |
| **Free-tier limits** | Gemini caps embeddings/chat per minute *and* per day | Paid tier, or queue + spread the work |
| **URL fetch** | JS-rendered pages, paywalls | Headless browser (Playwright) |
| **Single-turn RAG** | Follow-ups like "what about its pricing?" lack prior context | Feed recent turns in, or rewrite follow-ups into standalone questions |
| **Retrieval quality** | Fixed `top_k`, no reranking | Reranker model; hybrid keyword + vector search |

## What I'd add for production

- **Async ingestion** with a job queue and status polling
- **Reranking + hybrid search** for retrieval quality
- **Multi-turn conversational context**
- **Retrieval evals** (golden Q&A set) to tune chunking, `top_k`, and prompts
- **Observability:** tracing, token/cost metrics, latency histograms
- **Encryption at rest** for stored MCP auth tokens

---

## Debuggability

- **Structured logging** — one logger per module, key=value events
  (`item_ingested item_id=… chunks=7`, `query_answered … tool_calls=1`,
  `mcp_tool_call server=… tool=…`, `quota_exceeded …`). Noisy third-party loggers quieted.
- **Domain errors → HTTP status codes** via a small exception hierarchy (`app/errors.py`)
  and one FastAPI handler, so clients always get a clean `{ "detail": … }`.
- **Input validation** in Pydantic schemas — bad shapes are rejected with a clear `422`
  before any work (or spend) happens.

---

## Project structure

```
backend/app/
  main.py              # app wiring, CORS, lifespan (DB pool + MCP session), error handler
  config.py            # env-driven settings
  auth.py              # verifies the Supabase JWT -> user_id (dependency)
  db.py                # Postgres pool (psycopg) + pgvector registration
  schemas.py           # Pydantic request/response models
  errors.py            # domain exceptions -> HTTP status codes
  logging_config.py    # structured logging
  repository.py        # all SQL, every query scoped to a user_id
  mcp_demo_server.py   # bundled demo MCP server, mounted at /mcp-demo
  routers/
    items.py           # POST /ingest, POST /ingest/document, GET /items
    query.py           # POST /query
    conversations.py   # chat history CRUD
    usage.py           # GET /usage
    mcp_servers.py     # MCP server CRUD
  services/
    ingestion.py       # fetch URL + extract text; normalize notes
    documents.py       # extract text from PDF / DOCX / TXT / MD
    chunking.py        # chunking strategy
    embeddings.py      # Gemini embeddings (batching, rate-limit handling)
    gemini_client.py   # Gemini client singleton
    ingest_pipeline.py # get text -> chunk -> embed -> persist
    rag.py             # retrieve -> tool-calling loop -> grounded answer
    chat.py            # conversation/message persistence around a query
    usage.py           # token quota metering + enforcement
    mcp_client.py      # connects to remote MCP servers (SSRF-checked)
    mcp_tools.py       # bridges MCP tools into Gemini function calling
    security.py        # SSRF protection for user-supplied URLs
  tests/               # offline unit tests (no network/API key needed)

frontend/src/
  api.ts               # single API client (auth header, error normalization)
  types.ts             # shared types mirroring backend schemas
  supabase.ts          # Supabase client
  App.tsx              # auth gate: spinner -> Login -> Inbox
  hooks/
    useAuth.ts         # Supabase session state
    useTypewriter.ts   # progressive answer reveal
  components/
    Login.tsx           # Google sign-in
    Inbox.tsx           # main app: state + layout
    Sidebar.tsx         # chats, knowledge base, usage bar, MCP entry
    ChatThread.tsx      # conversation + empty state
    MessageBubble.tsx   # one message (+ tool chips, sources)
    Composer.tsx        # chat input, + button to add knowledge
    AddItemModal.tsx    # add note / link / document
    McpServersModal.tsx # connect & manage MCP servers
    SourceCitations.tsx # expandable cited chunks
    ToolCallChips.tsx   # MCP tools used in an answer

supabase/schema.sql    # tables, indexes, RLS policies, match_chunks()
```

---

## Tests

Offline unit tests (no network, no API key, no database needed):

```bash
cd backend
pip install pytest
pytest -q
```

---

## Deployment

Deployed as a monorepo: backend on **Render** (`rootDir: backend`, see
[`render.yaml`](render.yaml)), frontend on **Netlify** (`base: frontend`, see
[`netlify.toml`](netlify.toml)).

After deploying, set `CORS_ORIGINS` on the backend to the frontend URL, and add the
frontend URL to Supabase's Site URL + Redirect URLs.

> On Render's free tier the service spins down when idle, so the first request after
> a pause can take ~30–60s to wake.
