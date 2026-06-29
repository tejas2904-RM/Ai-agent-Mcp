import type { PulsePayload, TopThemeInsight, TraceableQuote, ActionIdea } from "./types";

export function isApiError(error: unknown): error is { status: number; message: string } {
  return (
    typeof error === "object" &&
    error !== null &&
    "status" in error &&
    typeof (error as { status: unknown }).status === "number"
  );
}

export function normalizePulse(pulse: PulsePayload): PulsePayload {
  return {
    ...pulse,
    top_themes: (pulse.top_themes ?? []) as TopThemeInsight[],
    quotes: (pulse.quotes ?? []) as TraceableQuote[],
    action_ideas: (pulse.action_ideas ?? []) as ActionIdea[],
    delivery: pulse.delivery ?? { document_url: null, draft_id: null },
    word_count: pulse.word_count ?? 0,
    note_content: pulse.note_content ?? "",
    title: pulse.title ?? "Weekly Review Pulse",
    week_range: pulse.week_range ?? "Unknown week",
  };
}

export function isLocalApiUrl(apiBase: string): boolean {
  try {
    const { hostname } = new URL(apiBase);
    return hostname === "localhost" || hostname === "127.0.0.1";
  } catch {
    return false;
  }
}

export function apiErrorMessage(error: unknown, apiBase: string): string {
  if (isApiError(error)) {
    if (error.status === 0) {
      return `Could not reach the API at ${apiBase}. The backend may be starting up or the URL may be wrong.`;
    }
    if (error.status >= 500) {
      return `The API at ${apiBase} returned a server error (${error.status}). Try again in a minute.`;
    }
    return error.message || `API request failed (${error.status}).`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "An unexpected error occurred while loading pulse data.";
}
