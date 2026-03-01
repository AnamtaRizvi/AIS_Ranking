const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export type OrgRanking = {
  organization: string;
  country_code: string;
  counts: Record<string, number>;
  total: number;
};

export async function fetchOrgRankings(journalCode?: string): Promise<OrgRanking[]> {
  const url = journalCode
    ? `${API_BASE}/org-rankings?journal_code=${encodeURIComponent(journalCode)}`
    : `${API_BASE}/org-rankings`;
  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to fetch org rankings");
  return res.json();
}

export type DebugSummary = {
  per_journal: { code: string; name: string; paper_count: number }[];
  top_orgs_overall: { organization: string; total: number }[];
};

export async function fetchDebugSummary(): Promise<DebugSummary> {
  const res = await fetch(`${API_BASE}/debug/summary`);
  if (!res.ok) throw new Error("Failed to fetch debug summary");
  return res.json();
}

export type JournalWithCounts = {
  code: string;
  name: string;
  paper_count: number;
  counts: Record<string, number>;
};

export async function fetchJournals(): Promise<JournalWithCounts[]> {
  const res = await fetch(`${API_BASE}/journals`);
  if (!res.ok) throw new Error("Failed to fetch journals");
  return res.json();
}
