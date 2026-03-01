"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export default function Header() {
  const pathname = usePathname();
  const rankingsActive = pathname === "/";

  return (
    <header className="border-b border-[#E5E7EB] bg-white shadow-sm">
      <div className="mx-auto flex max-w-[1400px] items-center justify-between gap-4 px-6 py-4">
        <h1 className="text-xl font-semibold text-[#111827]">
          <span className="text-[#CC0033]">Rutgers</span> AIS
        </h1>
        <nav className="flex gap-1">
          <Link
            href="/"
            className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              rankingsActive
                ? "bg-[#CC0033] text-white"
                : "text-[#111827] hover:bg-[#F7F7F8] hover:text-[#CC0033]"
            }`}
          >
            Rankings
          </Link>
        </nav>
      </div>
    </header>
  );
}
