"use client";

import { useMemo, useState } from "react";
import type { RunSummary } from "@/lib/types";
import { Pill } from "./Pill";

interface RunTimelineProps {
  runs: RunSummary[];
}

type FilterStatus = "all" | "success" | "failed" | "running" | "skipped";

export function RunTimeline({ runs }: RunTimelineProps) {
  const [filter, setFilter] = useState<FilterStatus>("all");

  const filtered = useMemo(() => {
    if (filter === "all") return runs;
    if (filter === "skipped") return runs.filter((r) => r.delivery_skipped);
    return runs.filter((r) => r.status.toLowerCase() === filter);
  }, [runs, filter]);

  const chips: { key: FilterStatus; label: string }[] = [
    { key: "all", label: "All" },
    { key: "success", label: "Success" },
    { key: "failed", label: "Failed" },
    { key: "running", label: "Running" },
    { key: "skipped", label: "Skipped delivery" },
  ];

  return (
    <div>
      <div className="mb-6 flex flex-wrap gap-2">
        {chips.map((chip) => (
          <button
            key={chip.key}
            type="button"
            onClick={() => setFilter(chip.key)}
            className={`rounded-full px-3 py-1 text-sm font-medium transition-colors ${
              filter === chip.key
                ? "bg-primary text-white"
                : "border border-border bg-surface text-secondary hover:border-primary"
            }`}
          >
            {chip.label}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <p className="text-sm text-muted">No runs match this filter.</p>
      ) : (
        <ol className="space-y-4">
          {filtered.map((run) => (
            <li
              key={run.run_id}
              className="rounded-card border border-border bg-surface p-5 shadow-card"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-heading">
                    {run.week_range ?? "Unknown week"}
                  </p>
                  <p className="mt-0.5 font-mono text-xs text-muted">{run.run_id}</p>
                </div>
                <Pill label={run.status} variant="status" />
              </div>
              <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
                <div>
                  <dt className="text-xs text-muted">Started</dt>
                  <dd className="text-heading">{formatDate(run.started_at)}</dd>
                </div>
                <div>
                  <dt className="text-xs text-muted">Completed</dt>
                  <dd className="text-heading">
                    {run.completed_at ? formatDate(run.completed_at) : "—"}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-muted">Note words</dt>
                  <dd className="text-heading">{run.note_word_count ?? "—"}</dd>
                </div>
                <div>
                  <dt className="text-xs text-muted">Flags</dt>
                  <dd className="flex flex-wrap gap-1">
                    {run.is_rerun && <Pill label="rerun" variant="neutral" />}
                    {run.delivery_skipped && <Pill label="delivery skipped" variant="neutral" />}
                    {!run.is_rerun && !run.delivery_skipped && (
                      <span className="text-muted">—</span>
                    )}
                  </dd>
                </div>
              </dl>
              {run.document_url && (
                <a
                  href={run.document_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-3 inline-block text-sm text-primary hover:underline"
                >
                  Open Google Doc →
                </a>
              )}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString("en-IN", {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}
