import type { Thesis, ThesisCheck, ThesisDetail } from "../types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export function listTheses(): Promise<Thesis[]> {
  return request("/api/theses");
}

export function getThesis(id: number): Promise<ThesisDetail> {
  return request(`/api/theses/${id}`);
}

export function createThesis(input: { ticker: string; thesis_text: string }): Promise<Thesis> {
  return request("/api/theses", { method: "POST", body: JSON.stringify(input) });
}

export function triggerCheck(thesisId: number): Promise<ThesisCheck> {
  return request(`/api/theses/${thesisId}/checks`, { method: "POST" });
}
