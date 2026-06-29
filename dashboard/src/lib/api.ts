import type { PulsePayload, RunSummary, WeekSummary } from "./types";
import { resolveApiBaseUrl } from "./config";
import { connection } from "next/server";

const API_TIMEOUT_MS = 30_000;

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  // Ensure env vars are read at request time, not frozen from build.
  await connection();

  const apiBase = resolveApiBaseUrl();
  let response: Response;

  try {
    response = await fetch(`${apiBase}${path}`, {
      ...init,
      headers: {
        Accept: "application/json",
        ...init?.headers,
      },
      cache: "no-store",
      signal: AbortSignal.timeout(API_TIMEOUT_MS),
    });
  } catch (cause) {
    const message =
      cause instanceof Error ? cause.message : "Failed to reach API";
    throw new ApiError(message, 0);
  }

  if (!response.ok) {
    const detail = await response.text();
    let message = detail || `API error ${response.status}`;
    try {
      const body = JSON.parse(detail) as { detail?: unknown };
      if (typeof body.detail === "string") {
        message = body.detail;
      }
    } catch {
      // keep raw text
    }
    throw new ApiError(message, response.status);
  }

  return response.json() as Promise<T>;
}

export function getApiBaseUrl(): string {
  return resolveApiBaseUrl();
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
