import type { PulsePayload, RunSummary, WeekSummary } from "./types";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
);

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...init?.headers,
    },
    next: { revalidate: 3600 },
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new ApiError(detail || `API error ${response.status}`, response.status);
  }

  return response.json() as Promise<T>;
}

export function getApiBaseUrl(): string {
  return API_BASE;
}

export async function fetchLatestPulse(): Promise<PulsePayload> {
  return fetchJson<PulsePayload>("/api/v1/pulse/latest");
}

export async function fetchPulseForWeek(weekRange: string): Promise<PulsePayload> {
  return fetchJson<PulsePayload>(
    `/api/v1/pulse/weeks/${encodeURIComponent(weekRange)}`,
  );
}

export async function fetchWeeks(): Promise<WeekSummary[]> {
  return fetchJson<WeekSummary[]>("/api/v1/pulse/weeks");
}

export async function fetchRuns(): Promise<RunSummary[]> {
  return fetchJson<RunSummary[]>("/api/v1/runs");
}
