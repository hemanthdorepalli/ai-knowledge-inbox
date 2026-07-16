// Mirrors the backend Pydantic schemas (see backend/app/schemas.py).
// Kept in one place so request/response shapes stay in sync across components.

export type SourceType = "note" | "url" | "document";

export interface Item {
  id: string;
  type: SourceType;
  title: string | null;
  source_url: string | null;
  snippet: string;
  created_at: string;
  chunk_count: number;
}

export interface IngestResponse {
  id: string;
  type: SourceType;
  title: string | null;
  source_url: string | null;
  created_at: string;
  chunk_count: number;
}

export interface SourceSnippet {
  item_id: string;
  title: string | null;
  source_url: string | null;
  chunk_text: string;
  score: number;
}

export interface QueryResponse {
  answer: string;
  sources: SourceSnippet[];
  conversation_id: string;
}

export interface Conversation {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

// A message as stored/loaded from history (POST /query persists these).
export interface MessageOut {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceSnippet[] | null;
  created_at: string;
}

// Request bodies for POST /ingest. Exactly one of content/url is used,
// selected by `type` (the backend validates this too).
export type IngestRequest =
  | { type: "note"; content: string; title?: string }
  | { type: "url"; url: string; title?: string };

// A single turn in the chat thread. `pending` marks an assistant message that
// is still waiting on /query; `error` marks one whose request failed.
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceSnippet[];
  pending?: boolean;
  error?: boolean;
}
