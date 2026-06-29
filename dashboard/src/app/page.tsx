import Link from "next/link";
import { NavBar } from "@/components/NavBar";
import { ThemeCard } from "@/components/ThemeCard";
import { QuoteCard } from "@/components/QuoteCard";
import { ActionList } from "@/components/ActionList";
import { WeeklyNotePreview } from "@/components/WeeklyNotePreview";
import { EmptyState } from "@/components/EmptyState";
import { ApiError, fetchLatestPulse, fetchPulseForWeek, fetchWeeks } from "@/lib/api";
import type { WeekSummary } from "@/lib/types";

interface PageProps {
  searchParams: Promise<{ week?: string }>;
}

export default async function DashboardPage({ searchParams }: PageProps) {
  const { week } = await searchParams;

  let weeks: WeekSummary[];
  try {
    weeks = await fetchWeeks();
  } catch {
    weeks = [];
  }

  let pulse;
  try {
    pulse = week ? await fetchPulseForWeek(week) : await fetchLatestPulse();
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return (
        <PageShell weeks={weeks}>
          <EmptyState
            title="No pulse data yet"
            description="Run the weekly pipeline or sync artifacts to the API. Once data is available, the latest weekly insights will appear here."
            actionLabel="View run history"
            actionHref="/runs"
          />
        </PageShell>
      );
    }
    throw error;
  }

  const currentWeek = weeks.find((w) => w.week_range === pulse.week_range);
  const runStatus = currentWeek?.status ?? "success";

  return (
    <PageShell
      weeks={weeks}
      currentWeek={pulse.week_range}
      status={runStatus}
      documentUrl={pulse.delivery.document_url}
      draftId={pulse.delivery.draft_id}
    >
      <section className="mb-10">
        <p className="text-sm font-medium text-primary">{pulse.week_range}</p>
        <h1 className="mt-1 text-balance text-3xl font-bold tracking-tight text-heading">
          {pulse.title}
        </h1>
        <p className="mt-2 text-sm text-secondary">
          {pulse.word_count} words
          {pulse.generated_at && (
            <>
              {" "}
              · Generated{" "}
              {new Date(pulse.generated_at).toLocaleString("en-IN", {
                dateStyle: "medium",
                timeStyle: "short",
              })}
            </>
          )}
          {pulse.run_id && (
            <>
              {" "}
              · Run <span className="font-mono text-xs">{pulse.run_id}</span>
            </>
          )}
        </p>
      </section>

      <section className="mb-10">
        <h2 className="mb-4 text-xl font-semibold text-heading">Top Themes</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {pulse.top_themes.map((theme) => (
            <ThemeCard key={theme.rank} theme={theme} />
          ))}
        </div>
      </section>

      <section className="mb-10 grid gap-8 lg:grid-cols-2">
        <div>
          <h2 className="mb-4 text-xl font-semibold text-heading">User Quotes</h2>
          <div className="space-y-3">
            {pulse.quotes.length === 0 ? (
              <p className="text-sm text-muted">No traceable quotes this week.</p>
            ) : (
              pulse.quotes.map((quote, index) => (
                <QuoteCard key={`${quote.review_id}-${index}`} quote={quote} />
              ))
            )}
          </div>
        </div>
        <div>
          <h2 className="mb-4 text-xl font-semibold text-heading">Action Ideas</h2>
          <ActionList actions={pulse.action_ideas} />
        </div>
      </section>

      <WeeklyNotePreview content={pulse.note_content} wordCount={pulse.word_count} />
    </PageShell>
  );
}

interface PageShellProps {
  children: React.ReactNode;
  weeks?: Awaited<ReturnType<typeof fetchWeeks>>;
  currentWeek?: string;
  status?: string;
  documentUrl?: string | null;
  draftId?: string | null;
}

function PageShell({
  children,
  weeks = [],
  currentWeek,
  status,
  documentUrl,
  draftId,
}: PageShellProps) {
  return (
    <>
      <NavBar
        weeks={weeks}
        currentWeek={currentWeek}
        status={status}
        documentUrl={documentUrl}
      />
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        {draftId && (
          <p className="mb-4 text-sm text-secondary">
            Gmail draft ready ·{" "}
            <span className="font-mono text-xs text-muted">{draftId}</span>
          </p>
        )}
        {children}
      </main>
      <footer className="border-t border-border py-6 text-center text-xs text-muted">
        <Link href="/runs" className="hover:text-primary">
          Run history
        </Link>
        {" · "}
        Groww Review Pulse
      </footer>
    </>
  );
}
