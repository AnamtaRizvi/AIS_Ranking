"use client";

import type { CategoryOrgCount } from "@/components/categoryRanking";

type Props = {
  category: string;
  topOrgs: CategoryOrgCount[];
  onOpen: () => void;
};

export default function CategoryCard({ category, topOrgs, onOpen }: Props) {
  return (
    <button
      type="button"
      onClick={onOpen}
      className="w-full rounded-lg border border-[#E5E7EB] bg-white p-4 text-left shadow-sm transition-transform hover:-translate-y-0.5 hover:shadow-md"
    >
      <h3 className="text-base font-semibold text-[#111827]">{category}</h3>
      <ul className="mt-3 space-y-2 text-sm">
        {topOrgs.length === 0 ? (
          <li className="text-gray-500">No organizations with papers in this category.</li>
        ) : (
          topOrgs.map((org, idx) => (
            <li key={`${category}-${org.org}`} className="flex items-center justify-between text-[#111827]">
              <span>
                {idx + 1}. {org.org}
              </span>
              <span className="font-medium">{org.count}</span>
            </li>
          ))
        )}
      </ul>
      <div className="mt-4 text-sm font-medium text-[#CC0033]">View full ranking -&gt;</div>
    </button>
  );
}
