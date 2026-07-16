// Single place that knows how to talk to the backend. Components call these
// functions and never touch fetch() directly, so error handling and the base
// URL live in exactly one file.

import type {
  Conversation,
  IngestRequest,
  IngestResponse,
  Item,
  MessageOut,
  QueryResponse,
  Usage,
} from "./types";
import { supabase } from "./supabase";

// Strip any trailing slash so `${API_BASE}${path}` never produces a double
// slash regardless of how the env var is set (e.g. "...onrender.com/").
const API_BASE = (import.meta.env.VITE_API_BASE ?? "http://localhost:8000").replace(/\/+$/, "");

// The backend requires a logged-in user, so every request carries the current
// Supabase access token as a bearer token.
async function authHeader(): Promise<Record<string, string>> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// The backend returns two error shapes:
//   - domain errors:      { detail: "human readable message" }
//   - validation errors:  { detail: [{ msg, loc, ... }] }  (FastAPI/Pydantic)
// This normalizes both into a single Error message the UI can show.
export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(await authHeader()),
        ...init?.headers,
      },
    });
  } catch {
    throw new ApiError(0, `Cannot reach the API at ${API_BASE}. Is the backend running?`);
  }

  if (!response.ok) {
    throw new ApiError(response.status, await extractErrorMessage(response));
  }

  // 204/empty-body safety, though our endpoints always return JSON.
  const text = await response.text();
  return (text ? JSON.parse(text) : null) as T;
}

async function extractErrorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      return body.detail.map((e: { msg?: string }) => e.msg ?? "invalid input").join("; ");
    }
  } catch {
    /* fall through to generic message */
  }
  return `Request failed with status ${response.status}`;
}

export function fetchItems(): Promise<Item[]> {
  return request<Item[]>("/items");
}

export function ingest(body: IngestRequest): Promise<IngestResponse> {
  return request<IngestResponse>("/ingest", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function query(
  question: string,
  conversationId?: string | null
): Promise<QueryResponse> {
  return request<QueryResponse>("/query", {
    method: "POST",
    body: JSON.stringify({ question, conversation_id: conversationId ?? null }),
  });
}

export function listConversations(): Promise<Conversation[]> {
  return request<Conversation[]>("/conversations");
}

export function getMessages(conversationId: string): Promise<MessageOut[]> {
  return request<MessageOut[]>(`/conversations/${conversationId}/messages`);
}

export function deleteConversation(conversationId: string): Promise<void> {
  return request<void>(`/conversations/${conversationId}`, { method: "DELETE" });
}

export function getUsage(): Promise<Usage> {
  return request<Usage>("/usage");
}

// File upload can't use request(): it sends multipart/form-data, so we must NOT
// set Content-Type (the browser adds it with the correct boundary).
export async function ingestDocument(file: File, title?: string): Promise<IngestResponse> {
  const form = new FormData();
  form.append("file", file);
  if (title) form.append("title", title);

  let response: Response;
  try {
    response = await fetch(`${API_BASE}/ingest/document`, {
      method: "POST",
      headers: await authHeader(),
      body: form,
    });
  } catch {
    throw new ApiError(0, `Cannot reach the API at ${API_BASE}. Is the backend running?`);
  }

  if (!response.ok) {
    throw new ApiError(response.status, await extractErrorMessage(response));
  }
  return (await response.json()) as IngestResponse;
}
