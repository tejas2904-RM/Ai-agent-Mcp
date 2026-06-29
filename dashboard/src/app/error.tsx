"use client";

import Link from "next/link";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-canvas px-4 text-center">
      <h1 className="text-2xl font-bold text-heading">Something went wrong</h1>
      <p className="mt-2 max-w-md text-sm text-secondary">
        {error.message || "Could not load dashboard data. Check that the API is running."}
      </p>
      <div className="mt-6 flex gap-3">
        <button
          type="button"
          onClick={reset}
          className="rounded-button bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/90"
        >
          Try again
        </button>
        <Link
          href="/"
          className="rounded-button border border-border bg-surface px-4 py-2 text-sm font-medium text-secondary hover:border-primary"
        >
          Home
        </Link>
      </div>
    </div>
  );
}
