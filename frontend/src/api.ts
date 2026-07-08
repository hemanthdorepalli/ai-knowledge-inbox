// Single place that knows how to talk to the backend. Components call these
// functions and never touch fetch() directly, so error handling and the base
// URL live in exactly one file.

import type {
  IngestRequest,
  IngestResponse,
  Item,
  QueryResponse,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

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
      headers: { "Content-Type": "application/json", ...init?.headers },
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

export function query(question: string): Promise<QueryResponse> {
  return request<QueryResponse>("/query", {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}
