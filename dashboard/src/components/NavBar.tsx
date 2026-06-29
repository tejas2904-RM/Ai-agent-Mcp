"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { WeekSummary } from "@/lib/types";

interface NavBarProps {
  weeks: WeekSummary[];
  currentWeek?: string;
  status?: string;
  documentUrl?: string | null;
}

export function NavBar({ weeks, currentWeek, status, documentUrl }: NavBarProps) {
  const pathname = usePathname();
  const isRuns = pathname === "/runs";

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-surface/95 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-sm font-bold text-white">
              G
            </span>
            <span className="hidden font-semibold text-heading sm:inline">
              Groww Review Pulse
            </span>
          </Link>
          <nav className="hidden items-center gap-1 sm:flex">
            <Link
              href="/"
              className={`rounded-button px-3 py-1.5 text-sm font-medium ${
                !isRuns ? "bg-primary/10 text-primary" : "text-secondary hover:text-heading"
              }`}
            >
              Dashboard
            </Link>
            <Link
              href="/runs"
              className={`rounded-button px-3 py-1.5 text-sm font-medium ${
                isRuns ? "bg-primary/10 text-primary" : "text-secondary hover:text-heading"
              }`}
            >
              Run History
            </Link>
          </nav>
        </div>

        <div className="flex items-center gap-3">
          {!isRuns && weeks.length > 0 && (
            <label className="hidden items-center gap-2 sm:flex">
              <span className="text-xs text-muted">Week</span>
              <select
                className="rounded-button border border-border bg-surface px-2 py-1.5 text-sm text-heading"
                defaultValue={currentWeek}
                onChange={(e) => {
                  if (e.target.value) {
                    window.location.href = `/?week=${encodeURIComponent(e.target.value)}`;
                  }
                }}
              >
                {weeks.map((w) => (
                  <option key={w.week_range} value={w.week_range}>
                    {w.week_range}
                  </option>
                ))}
              </select>
            </label>
          )}

          {documentUrl && (
            <a
              href={documentUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="hidden rounded-button border border-border px-3 py-1.5 text-sm text-secondary hover:border-primary hover:text-primary sm:inline-flex"
            >
              Google Doc
            </a>
          )}

          {status && (
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${
                status === "success"
                  ? "bg-positive/10 text-positive"
                  : status === "failed"
                    ? "bg-negative/10 text-negative"
                    : "bg-muted/15 text-secondary"
              }`}
            >
              {status}
            </span>
          )}
        </div>
      </div>
    </header>
  );
}
