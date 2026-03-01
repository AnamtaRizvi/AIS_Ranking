"use client";

import { useMemo } from "react";
import CategoryCard from "@/components/CategoryCard";
import { getCategoryList, getTopOrgsForCategory, type CategoryRow } from "@/components/categoryRanking";

type Props = {
  rows: CategoryRow[];
  onSelectCategory: (category: string) => void;
};

export default function CategoryGrid({ rows, onSelectCategory }: Props) {
  const categories = useMemo(() => getCategoryList(rows), [rows]);

  const cardData = useMemo(
    () =>
      categories.map((category) => ({
        category,
        topOrgs: getTopOrgsForCategory(rows, category, 3),
      })),
    [categories, rows]
  );

  if (categories.length === 0) {
    return (
      <div className="rounded-lg border border-[#E5E7EB] bg-white p-8 text-center text-[#111827]">
        No category data available for the selected filters.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
      {cardData.map(({ category, topOrgs }) => (
        <CategoryCard
          key={category}
          category={category}
          topOrgs={topOrgs}
          onOpen={() => onSelectCategory(category)}
        />
      ))}
    </div>
  );
}
