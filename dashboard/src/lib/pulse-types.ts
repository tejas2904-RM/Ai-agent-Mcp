import type { PulsePayload, WeekSummary } from "@/lib/types";

export type PulsePageResult =
  | { kind: "ok"; pulse: PulsePayload; weeks: WeekSummary[] }
  | { kind: "empty"; weeks: WeekSummary[] }
  | { kind: "error"; message: string; weeks: WeekSummary[]; apiBase: string };
