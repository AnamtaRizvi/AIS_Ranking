export type CategoryRow = {
  org: string;
  country: string;
  total: number;
  categories: Record<string, number>;
};

export type CategoryOrgCount = {
  org: string;
  country: string;
  count: number;
};

export function getCategoryList(rows: CategoryRow[]): string[] {
  const set = new Set<string>();
  for (const row of rows) {
    for (const name of Object.keys(row.categories || {})) {
      set.add(name);
    }
  }
  return Array.from(set).sort((a, b) => a.localeCompare(b));
}

export function getTopOrgsForCategory(
  rows: CategoryRow[],
  category: string,
  n: number
): CategoryOrgCount[] {
  return rows
    .map((row) => ({
      org: row.org,
      country: row.country,
      count: row.categories[category] ?? 0,
    }))
    .filter((row) => row.count > 0)
    .sort((a, b) => {
      if (b.count !== a.count) return b.count - a.count;
      return a.org.localeCompare(b.org);
    })
    .slice(0, n);
}
