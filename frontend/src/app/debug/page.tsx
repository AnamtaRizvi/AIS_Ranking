"use client";

import { useEffect, useState } from "react";
import { fetchDebugSummary, type DebugSummary } from "@/lib/api";

export default function DebugPage() {
  const [data, setData] = useState<DebugSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDebugSummary()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-[320px] items-center justify-center rounded-lg border border-[#E5E7EB] bg-white">
        <p className="text-[#111827]">Loading debug summary…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-red-800">
        <p className="font-medium">Error loading debug summary</p>
        <p className="mt-1 text-sm">{error}</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="rounded-lg border border-[#E5E7EB] bg-white p-8 text-center text-[#111827]">
        No data.
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <section className="overflow-hidden rounded-lg border border-[#E5E7EB] bg-white shadow-sm">
        <h2 className="border-b border-[#E5E7EB] bg-[#F7F7F8] px-6 py-3 text-lg font-semibold text-[#111827]">
          Papers per journal
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-[#E5E7EB] bg-[#F7F7F8]">
                <th className="p-3 font-medium text-[#111827]">Code</th>
                <th className="p-3 font-medium text-[#111827]">Name</th>
                <th className="p-3 font-medium text-[#111827] text-right">Paper count</th>
              </tr>
            </thead>
            <tbody>
              {data.per_journal.map((j) => (
                <tr
                  key={j.code}
                  className="border-b border-[#E5E7EB] hover:bg-[#CC0033]/5"
                >
                  <td className="p-3 font-medium text-[#111827]">{j.code}</td>
                  <td className="p-3 text-[#111827]">{j.name}</td>
                  <td className="p-3 text-right text-[#111827]">{j.paper_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="overflow-hidden rounded-lg border border-[#E5E7EB] bg-white shadow-sm">
        <h2 className="border-b border-[#E5E7EB] bg-[#F7F7F8] px-6 py-3 text-lg font-semibold text-[#111827]">
          Top organizations overall
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-[#E5E7EB] bg-[#F7F7F8]">
                <th className="p-3 font-medium text-[#111827]">Organization</th>
                <th className="p-3 font-medium text-[#111827] text-right">Total</th>
              </tr>
            </thead>
            <tbody>
              {data.top_orgs_overall.map((o, i) => (
                <tr
                  key={i}
                  className="border-b border-[#E5E7EB] hover:bg-[#CC0033]/5"
                >
                  <td className="p-3 text-[#111827]">{o.organization}</td>
                  <td className="p-3 text-right font-medium text-[#111827]">{o.total}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
