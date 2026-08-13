export type Verdict = "on_track" | "diverging" | "unclear";

export interface Source {
  title: string | null;
  url: string;
}

export interface LinkRef {
  target_raw: string;
  alias: string | null;
  node_id: string | null;
  title: string | null;
}

export interface NodeSummary {
  id: string;
  title: string;
  tags: string[];
  excerpt: string;
  updated_at: string;
  latest_verdict: Verdict | null;
}

export interface CheckRead {
  id: string;
  node_id: string;
  verdict: Verdict;
  reasoning: string;
  sources: Source[];
  created_at: string;
}

export interface NodeDetail {
  id: string;
  title: string;
  path: string;
  tags: string[];
  body: string;
  content_hash: string;
  fm_error: string | null;
  created_at: string;
  updated_at: string;
  links_out: LinkRef[];
  backlinks: LinkRef[];
  checks: CheckRead[];
}

export interface GraphNode {
  id: string;
  title: string;
  verdict: Verdict | null;
  degree: number;
}

export interface GraphEdge {
  source: string;
  target: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  unresolved: string[];
}

export interface SyncReport {
  added: number;
  updated: number;
  removed: number;
  errors: string[];
}
