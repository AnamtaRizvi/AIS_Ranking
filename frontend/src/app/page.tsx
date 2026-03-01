"use client";

import { useEffect, useState, useMemo } from "react";
import { fetchOrgRankings, fetchJournals, type OrgRanking, type JournalWithCounts } from "@/lib/api";
import CategoryGrid from "@/components/CategoryGrid";
import CategoryLeaderboard from "@/components/CategoryLeaderboard";
import { getCategoryList, type CategoryRow } from "@/components/categoryRanking";

const CATEGORIES = [
  "Accounting & Financial AI",
  "Business Intelligence & Decision Support",
  "Information Systems & Applied Analytics",
  "Engineering & Industrial AI",
  "Core AI & Data Science Methods",
];

type SortKey = "rank" | "organization" | "country_code" | "total" | (typeof CATEGORIES)[number];
type ViewMode = "overall" | "category";

export default function Home() {
  const [data, setData] = useState<OrgRanking[] | null>(null);
  const [journals, setJournals] = useState<JournalWithCounts[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedCountry, setSelectedCountry] = useState<string>("US");
  const [sortKey, setSortKey] = useState<SortKey>("total");
  const [sortDesc, setSortDesc] = useState(true);
  const [selectedJournalCode, setSelectedJournalCode] = useState<string>("");
  const [viewMode, setViewMode] = useState<ViewMode>("overall");
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [topN, setTopN] = useState<number>(25);

  useEffect(() => {
    setLoading(true);
    fetchOrgRankings(selectedJournalCode || undefined)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [selectedJournalCode]); // "" = All journals

  useEffect(() => {
    fetchJournals()
      .then(setJournals)
      .catch(() => setJournals([]));
  }, []);

  const countryOptions = useMemo(() => {
    if (!data) return ["US"];
    const codes = new Set<string>();
    for (const row of data) {
      const code = (row.country_code || "").trim();
      if (code) codes.add(code);
    }
    return Array.from(codes).sort((a, b) => a.localeCompare(b));
  }, [data]);

  const byCountry = useMemo(() => {
    if (!data) return [];
    return selectedCountry === ""
      ? data
      : data.filter((row) => (row.country_code || "").toUpperCase() === selectedCountry.toUpperCase());
  }, [data, selectedCountry]);

  const rankByOrg = useMemo(() => {
    const ranked = [...byCountry].sort((a, b) => b.total - a.total);
    const map = new Map<string, number>();
    ranked.forEach((row, idx) => {
      map.set(row.organization, idx + 1);
    });
    return map;
  }, [byCountry]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return byCountry;
    return byCountry.filter((row) => row.organization.toLowerCase().includes(q));
  }, [byCountry, search]);

  const categoryRows = useMemo<CategoryRow[]>(
    () =>
      filtered.map((row) => ({
        org: row.organization,
        country: row.country_code || "",
        total: row.total,
        categories: row.counts,
      })),
    [filtered]
  );

  const categoryList = useMemo(() => getCategoryList(categoryRows), [categoryRows]);

  useEffect(() => {
    if (selectedCategory && !categoryList.includes(selectedCategory)) {
      setSelectedCategory(null);
    }
  }, [selectedCategory, categoryList]);

  const sorted = useMemo(() => {
    const list = [...filtered];
    const mult = sortDesc ? -1 : 1;
    list.sort((a, b) => {
      let va: string | number = "";
      let vb: string | number = "";
      if (sortKey === "rank" || sortKey === "total") {
        va = sortKey === "rank" ? (rankByOrg.get(a.organization) ?? Number.MAX_SAFE_INTEGER) : a.total;
        vb = sortKey === "rank" ? (rankByOrg.get(b.organization) ?? Number.MAX_SAFE_INTEGER) : b.total;
        return mult * (Number(va) - Number(vb));
      }
      if (sortKey === "organization") {
        va = a.organization.toLowerCase();
        vb = b.organization.toLowerCase();
      } else if (sortKey === "country_code") {
        va = (a.country_code || "").toLowerCase();
        vb = (b.country_code || "").toLowerCase();
      } else if (CATEGORIES.includes(sortKey)) {
        va = a.counts[sortKey] ?? 0;
        vb = b.counts[sortKey] ?? 0;
        return mult * (Number(va) - Number(vb));
      }
      return mult * String(va).localeCompare(String(vb));
    });
    return list;
  }, [filtered, sortKey, sortDesc, rankByOrg]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDesc((d) => !d);
    } else {
      setSortKey(key);
      setSortDesc(key === "organization" || key === "country_code" ? false : true);
    }
  };

  if (loading && !data) {
    return (
      <div className="flex min-h-[320px] items-center justify-center rounded-lg border border-[#E5E7EB] bg-white">
        <p className="text-[#111827]">Loading rankings…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-red-800">
        <p className="font-medium">Error loading rankings</p>
        <p className="mt-1 text-sm">{error}</p>
      </div>
    );
  }

  if (!data?.length) {
    return (
      <div className="rounded-lg border border-[#E5E7EB] bg-white p-8 text-center text-[#111827]">
        No rankings data. Run backend ingest and classify.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-4">
        <div className="inline-flex overflow-hidden rounded-md border border-[#E5E7EB] bg-white">
          <button
            type="button"
            onClick={() => setViewMode("overall")}
            className={`px-3 py-2 text-sm font-medium ${
              viewMode === "overall"
                ? "bg-[#CC0033] text-white"
                : "text-[#111827] hover:bg-[#F7F7F8]"
            }`}
          >
            Overall
          </button>
          <button
            type="button"
            onClick={() => {
              setViewMode("category");
              setSelectedCategory(null);
            }}
            className={`px-3 py-2 text-sm font-medium ${
              viewMode === "category"
                ? "bg-[#CC0033] text-white"
                : "text-[#111827] hover:bg-[#F7F7F8]"
            }`}
          >
            By Category
          </button>
        </div>
        <div>
          <label htmlFor="journal-select" className="sr-only">
            Filter by journal
          </label>
          <select
            id="journal-select"
            value={selectedJournalCode}
            onChange={(e) => setSelectedJournalCode(e.target.value)}
            className="rounded-md border border-[#E5E7EB] bg-white px-3 py-2 text-sm text-[#111827] focus:border-[#CC0033] focus:outline-none focus:ring-1 focus:ring-[#CC0033]"
          >
            <option value="">All journals (total)</option>
            {journals?.map((j) => (
              <option key={j.code} value={j.code}>
                {j.code} — {j.name}
              </option>
            ))}
          </select>
        </div>
        <input
          type="search"
          placeholder="Search organization…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="rounded-md border border-[#E5E7EB] bg-white px-3 py-2 text-sm text-[#111827] placeholder:text-gray-500 focus:border-[#CC0033] focus:outline-none focus:ring-1 focus:ring-[#CC0033]"
        />
        <div>
          <label htmlFor="country-select" className="sr-only">
            Filter by country
          </label>
          <select
            id="country-select"
            value={selectedCountry}
            onChange={(e) => setSelectedCountry(e.target.value)}
            className="rounded-md border border-[#E5E7EB] bg-white px-3 py-2 text-sm text-[#111827] focus:border-[#CC0033] focus:outline-none focus:ring-1 focus:ring-[#CC0033]"
          >
            <option value="">All countries</option>
            {countryOptions.map((code) => (
              <option key={code} value={code}>
                {code}
              </option>
            ))}
          </select>
        </div>
      </div>

      {viewMode === "overall" ? (
        <>
          <div className="overflow-hidden rounded-lg border border-[#E5E7EB] bg-white shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[1200px] text-left text-sm">
                <thead className="sticky top-0 z-10 bg-[#CC0033] text-white">
                  <tr>
                    <th
                      className="cursor-pointer select-none p-3 font-medium hover:bg-[#b3002e]"
                      onClick={() => handleSort("rank")}
                    >
                      Rank {sortKey === "rank" && (sortDesc ? "↓" : "↑")}
                    </th>
                    <th
                      className="cursor-pointer select-none p-3 font-medium hover:bg-[#b3002e]"
                      onClick={() => handleSort("organization")}
                    >
                      Organization {sortKey === "organization" && (sortDesc ? "↓" : "↑")}
                    </th>
                    <th
                      className="cursor-pointer select-none p-3 font-medium hover:bg-[#b3002e]"
                      onClick={() => handleSort("country_code")}
                    >
                      Country {sortKey === "country_code" && (sortDesc ? "↓" : "↑")}
                    </th>
                    <th
                      className="cursor-pointer select-none p-3 font-medium hover:bg-[#b3002e] text-right"
                      onClick={() => handleSort("total")}
                    >
                      Total {sortKey === "total" && (sortDesc ? "↓" : "↑")}
                    </th>
                    {CATEGORIES.map((c) => (
                      <th
                        key={c}
                        title={c}
                        className="cursor-pointer select-none min-w-[140px] max-w-[220px] p-3 font-medium hover:bg-[#b3002e] text-right"
                        onClick={() => handleSort(c)}
                      >
                        <span className="whitespace-normal break-words">{c}</span>{" "}
                        {sortKey === c && (sortDesc ? "↓" : "↑")}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((row, i) => {
                    return (
                      <tr
                        key={i}
                        className="border-t border-[#E5E7EB] hover:bg-[#CC0033]/5"
                      >
                        <td className="p-3 font-medium text-[#111827]">
                          {rankByOrg.get(row.organization) ?? i + 1}
                        </td>
                        <td className="p-3 font-medium text-[#111827]">{row.organization}</td>
                        <td className="p-3 text-[#111827]">{row.country_code || "—"}</td>
                        <td className="p-3 text-right font-semibold text-[#111827]">{row.total}</td>
                        {CATEGORIES.map((cat) => (
                          <td key={cat} className="p-3 text-right text-[#111827]">
                            {row.counts[cat] ?? 0}
                          </td>
                        ))}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
          <p className="text-sm text-gray-600">
            Top 50 organizations
            {selectedJournalCode ? " in selected journal" : ""}. Click a column header to sort.
          </p>
        </>
      ) : selectedCategory ? (
        <CategoryLeaderboard
          category={selectedCategory}
          rows={categoryRows}
          topN={topN}
          onTopNChange={setTopN}
          onBack={() => setSelectedCategory(null)}
        />
      ) : (
        <CategoryGrid rows={categoryRows} onSelectCategory={setSelectedCategory} />
      )}
    </div>
  );
}
