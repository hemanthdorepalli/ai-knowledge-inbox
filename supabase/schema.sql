-- ============================================================================
-- AI Knowledge Inbox — Supabase schema (Phase 1: data layer)
-- Run this in the Supabase SQL Editor (Dashboard → SQL Editor → New query).
-- Safe to re-run: everything uses "if not exists" / "or replace".
-- ============================================================================

-- 1. Enable the pgvector extension (gives us the `vector` type + similarity search).
create extension if not exists vector;

-- ----------------------------------------------------------------------------
-- 2. Tables
--    Every row is owned by a user (user_id -> auth.users). This is what makes
--    the app multi-tenant: each user only ever sees their own data.
-- ----------------------------------------------------------------------------

create table if not exists items (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null references auth.users(id) on delete cascade,
    type        text not null check (type in ('note', 'url', 'pdf', 'document')),
    title       text,
    source_url  text,
    raw_content text not null,
    created_at  timestamptz not null default now()
);

-- Embedding is vector(768): we ask Gemini for 768-dimensional embeddings.
-- Why 768 and not 3072? pgvector's HNSW index supports up to 2000 dimensions,
-- and 768 is smaller/cheaper while still high quality. (Set in the backend via
-- output_dimensionality.)
create table if not exists chunks (
    id          uuid primary key default gen_random_uuid(),
    item_id     uuid not null references items(id) on delete cascade,
    user_id     uuid not null references auth.users(id) on delete cascade,
    chunk_index int  not null,
    chunk_text  text not null,
    embedding   vector(768) not null,
    created_at  timestamptz not null default now()
);

-- ----------------------------------------------------------------------------
-- 3. Indexes
-- ----------------------------------------------------------------------------
create index if not exists idx_items_user      on items(user_id);
create index if not exists idx_chunks_user     on chunks(user_id);
create index if not exists idx_chunks_item     on chunks(item_id);

-- The vector index: HNSW with cosine distance. This is what makes similarity
-- search fast instead of a full scan.
create index if not exists idx_chunks_embedding
    on chunks using hnsw (embedding vector_cosine_ops);

-- ----------------------------------------------------------------------------
-- 4. Row-Level Security (RLS) — the multi-tenant guarantee.
--    With these policies on, a query can only ever touch rows where
--    user_id = the logged-in user's id (auth.uid()). Enforced by Postgres
--    itself, so even a bug in the API can't leak another user's data.
-- ----------------------------------------------------------------------------
alter table items  enable row level security;
alter table chunks enable row level security;

drop policy if exists "items_own_rows"  on items;
create policy "items_own_rows" on items
    for all
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

drop policy if exists "chunks_own_rows" on chunks;
create policy "chunks_own_rows" on chunks
    for all
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

-- ----------------------------------------------------------------------------
-- 5. Similarity search function.
--    Given a query embedding, return the top-k most similar chunks for a user,
--    with the parent item's title/url and a similarity score (1 = identical).
--    SECURITY INVOKER (default) means RLS still applies when called with a
--    user's token. p_user_id is an explicit filter used before auth is wired.
-- ----------------------------------------------------------------------------
create or replace function match_chunks(
    query_embedding vector(768),
    match_count     int  default 5,
    p_user_id       uuid default null
)
returns table (
    chunk_id   uuid,
    item_id    uuid,
    chunk_text text,
    title      text,
    source_url text,
    similarity float
)
language sql
stable
as $$
    select
        c.id                               as chunk_id,
        c.item_id,
        c.chunk_text,
        i.title,
        i.source_url,
        1 - (c.embedding <=> query_embedding) as similarity   -- <=> is cosine distance
    from chunks c
    join items i on i.id = c.item_id
    where (p_user_id is null or c.user_id = p_user_id)
    order by c.embedding <=> query_embedding                  -- nearest first
    limit match_count;
$$;

-- ----------------------------------------------------------------------------
-- 6. Chat history: conversations + messages.
--    Each conversation is a chat thread owned by a user; messages are its turns.
-- ----------------------------------------------------------------------------
create table if not exists conversations (
    id         uuid primary key default gen_random_uuid(),
    user_id    uuid not null references auth.users(id) on delete cascade,
    title      text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists messages (
    id              uuid primary key default gen_random_uuid(),
    conversation_id uuid not null references conversations(id) on delete cascade,
    user_id         uuid not null references auth.users(id) on delete cascade,
    role            text not null check (role in ('user', 'assistant')),
    content         text not null,
    sources         jsonb,   -- retrieved source snippets for assistant messages
    created_at      timestamptz not null default now()
);

create index if not exists idx_conversations_user    on conversations(user_id);
create index if not exists idx_messages_conversation  on messages(conversation_id);
create index if not exists idx_messages_user          on messages(user_id);

alter table conversations enable row level security;
alter table messages      enable row level security;

drop policy if exists "conversations_own_rows" on conversations;
create policy "conversations_own_rows" on conversations
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "messages_own_rows" on messages;
create policy "messages_own_rows" on messages
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
