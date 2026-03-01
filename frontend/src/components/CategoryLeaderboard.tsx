"use client";

import { useMemo } from "react";
import { getTopOrgsForCategory, type CategoryRow } from "@/components/categoryRanking";

type Props = {
  category: string;
  rows: CategoryRow[];
  topN: number;
  onTopNChange: (n: number) => void;
  onBack: () => void;
};

const TOP_N_OPTIONS = [10, 25, 50, 100];

export default function CategoryLeaderboard({
  category,
  rows,
  topN,
  onTopNChange,
  onBack,
}: Props) {
  const leaderboardRows = useMemo(
    () => getTopOrgsForCategory(rows, category, topN),
    [rows, category, topN]
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm">
          <button
            type="button"
            onClick={onBack}
            className="rounded-md border border-[#E5E7EB] bg-white px-3 py-1.5 text-[#111827] hover:bg-[#F7F7F8]"
          >
            Back
          </button>
          <span className="text-gray-500">Categories &gt;</span>
          <span className="font-medium text-[#111827]">{category}</span>
        </div>
        <label className="flex items-center gap-2 text-sm text-[#111827]">
          Top N
          <select
            value={topN}
            onChange={(e) => onTopNChange(Number(e.target.value))}
            className="rounded-md border border-[#E5E7EB] bg-white px-2 py-1.5 text-sm focus:border-[#CC0033] focus:outline-none focus:ring-1 focus:ring-[#CC0033]"
          >
            {TOP_N_OPTIONS.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="overflow-hidden rounded-lg border border-[#E5E7EB] bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[700px] text-left text-sm">
            <thead className="bg-[#CC0033] text-white">
              <tr>
                <th className="p-3 font-medium">Rank</th>
                <th className="p-3 font-medium">Organization</th>
                <th className="p-3 font-medium">Country</th>
                <th className="p-3 text-right font-medium">{category} Count</th>
              </tr>
            </thead>
            <tbody>
              {leaderboardRows.map((row, index) => (
                <tr key={`${row.org}-${index}`} className="border-t border-[#E5E7EB] hover:bg-[#CC0033]/5">
                  <td className="p-3 font-medium text-[#111827]">{index + 1}</td>
                  <td className="p-3 text-[#111827]">{row.org}</td>
                  <td className="p-3 text-[#111827]">{row.country || "-"}</td>
                  <td className="p-3 text-right font-medium text-[#111827]">{row.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
