export type Verdict = "on_track" | "diverging" | "unclear";

export interface Source {
  title: string | null;
  url: string;
}

export interface Thesis {
  id: number;
  ticker: string;
  thesis_text: string;
  created_at: string;
}

export interface ThesisCheck {
  id: number;
  thesis_id: number;
  verdict: Verdict;
  reasoning: string;
  sources: Source[];
  created_at: string;
}

export interface ThesisDetail extends Thesis {
  checks: ThesisCheck[];
}
