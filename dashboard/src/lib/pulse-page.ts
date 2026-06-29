import {
  fetchLatestPulse,
  fetchPulseForWeek,
  fetchWeeks,
  getApiBaseUrl,
} from "@/lib/api";
import type { PulsePayload, WeekSummary } from "@/lib/types";
import { apiErrorMessage, isApiError, normalizePulse } from "@/lib/utils";
import type { PulsePageResult } from "@/lib/pulse-types";

export async function loadPulsePage(week?: string): Promise<PulsePageResult> {
  let weeks: WeekSummary[] = [];
  try {
    weeks = await fetchWeeks();
  } catch {
    weeks = [];
  }

  const apiBase = getApiBaseUrl();

  try {
    const raw = week ? await fetchPulseForWeek(week) : await fetchLatestPulse();
    const pulse: PulsePayload = normalizePulse(raw);
    return { kind: "ok", pulse, weeks };
  } catch (error) {
    const status = isApiError(error) ? error.status : 0;
    if (status === 404) {
      return { kind: "empty", weeks };
    }
    return {
      kind: "error",
      message: apiErrorMessage(error, apiBase),
      weeks,
      apiBase,
    };
  }
}
