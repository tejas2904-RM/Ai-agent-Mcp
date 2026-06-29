import Link from "next/link";
import { NavBar } from "@/components/NavBar";
import { RunTimeline } from "@/components/RunTimeline";
import { EmptyState } from "@/components/EmptyState";
import { fetchRuns } from "@/lib/api";
import type { RunSummary } from "@/lib/types";

export default async function RunsPage() {
  let runs: RunSummary[];
  try {
    runs = await fetchRuns();
  } catch {
    runs = [];
  }

  return (
    <>
      <NavBar weeks={[]} />
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <nav className="mb-2 text-sm text-muted">
          <Link href="/" className="hover:text-primary">
            Dashboard
          </Link>
          <span className="mx-2">/</span>
          <span className="text-secondary">Run History</span>
        </nav>
        <h1 className="text-3xl font-bold text-heading">Run History</h1>
        <p className="mt-2 text-sm text-secondary">
          Pipeline runs from the weekly Groww Review Pulse orchestrator.
        </p>

        <div className="mt-8">
          {runs.length === 0 ? (
            <EmptyState
              title="No runs recorded"
              description="Weekly pipeline runs will appear here once orchestration has completed at least once."
              actionLabel="Back to dashboard"
              actionHref="/"
            />
          ) : (
            <RunTimeline runs={runs} />
          )}
        </div>
      </main>
    </>
  );
}
