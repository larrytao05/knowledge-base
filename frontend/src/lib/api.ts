import type {
  CheckRead,
  GraphData,
  NodeDetail,
  NodeSummary,
  SyncReport,
} from "../types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, body: unknown, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    let body: unknown = text;
    try {
      body = JSON.parse(text);
    } catch {
      // not JSON - keep the raw text
    }
    throw new ApiError(res.status, body, `${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export function listNodes(params?: { q?: string; tag?: string }): Promise<NodeSummary[]> {
  const query = new URLSearchParams();
  if (params?.q) query.set("q", params.q);
  if (params?.tag) query.set("tag", params.tag);
  const qs = query.toString();
  return request(`/api/nodes${qs ? `?${qs}` : ""}`);
}

export function getNode(id: string): Promise<NodeDetail> {
  return request(`/api/nodes/${id}`);
}

export function createNode(input: {
  title: string;
  body?: string;
  tags?: string[];
}): Promise<NodeDetail> {
  return request("/api/nodes", { method: "POST", body: JSON.stringify(input) });
}

export function updateNode(
  id: string,
  input: {
    content_hash: string;
    title?: string;
    body?: string;
    tags?: string[];
  },
): Promise<NodeDetail> {
  return request(`/api/nodes/${id}`, { method: "PATCH", body: JSON.stringify(input) });
}

export function runNodeCheck(id: string): Promise<CheckRead> {
  return request(`/api/nodes/${id}/checks`, { method: "POST" });
}

export function getGraph(): Promise<GraphData> {
  return request("/api/graph");
}

export function reindexVault(): Promise<SyncReport> {
  return request("/api/vault/reindex", { method: "POST" });
}
