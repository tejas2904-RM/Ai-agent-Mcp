import Link from "next/link";

interface EmptyStateProps {
  title: string;
  description: string;
  actionLabel?: string;
  actionHref?: string;
}

export function EmptyState({
  title,
  description,
  actionLabel,
  actionHref,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-card border border-border bg-surface px-6 py-16 text-center shadow-card">
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
        <svg
          className="h-6 w-6"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
      </div>
      <h2 className="text-lg font-semibold text-heading">{title}</h2>
      <p className="mt-2 max-w-md text-sm text-secondary">{description}</p>
      {actionLabel && actionHref && (
        <Link
          href={actionHref}
          className="mt-6 rounded-button bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/90"
        >
          {actionLabel}
        </Link>
      )}
    </div>
  );
}
