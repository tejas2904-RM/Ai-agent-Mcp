import type { WeekSummary } from "@/lib/types";

interface ApiUnavailableProps {
  title?: string;
  description: string;
  apiBase: string;
}

export function ApiUnavailable({
  title = "API unavailable",
  description,
  apiBase,
}: ApiUnavailableProps) {
  const showConfigHint =
    process.env.NODE_ENV === "production" && apiBase.includes("localhost");

  return (
    <div className="flex flex-col items-center justify-center rounded-card border border-border bg-surface px-6 py-16 text-center shadow-card">
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-mixed/10 text-mixed">
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
            d="M12 9v2m0 4h.01M5.07 19h13.86a2 2 0 001.74-3l-6.93-12a2 2 0 00-3.48 0l-6.93 12a2 2 0 001.74 3z"
          />
        </svg>
      </div>
      <h2 className="text-lg font-semibold text-heading">{title}</h2>
      <p className="mt-2 max-w-lg text-sm text-secondary">{description}</p>
      <p className="mt-4 font-mono text-xs text-muted">API: {apiBase}</p>
      {showConfigHint && (
        <p className="mt-3 max-w-lg text-xs text-mixed">
          Set <span className="font-mono">NEXT_PUBLIC_API_URL</span> in Vercel to your
          Render API URL (e.g. https://groww-pulse-api.onrender.com).
        </p>
      )}
    </div>
  );
}
