import type { SentimentSignal, VolumeSignal } from "@/lib/types";

const volumeStyles: Record<VolumeSignal, string> = {
  high: "bg-primary/10 text-primary",
  medium: "bg-mixed/10 text-mixed",
  low: "bg-muted/15 text-secondary",
};

const sentimentStyles: Record<SentimentSignal, string> = {
  negative: "bg-negative/10 text-negative",
  mixed: "bg-mixed/10 text-mixed",
  positive: "bg-positive/10 text-positive",
};

interface PillProps {
  label: string;
  variant?: "volume" | "sentiment" | "status" | "neutral";
  signal?: VolumeSignal | SentimentSignal;
}

const statusStyles: Record<string, string> = {
  success: "bg-positive/10 text-positive",
  failed: "bg-negative/10 text-negative",
  running: "bg-mixed/10 text-mixed",
  skipped: "bg-muted/15 text-secondary",
};

export function Pill({ label, variant = "neutral", signal }: PillProps) {
  let className = "bg-muted/15 text-secondary";

  if (variant === "volume" && signal) {
    className = volumeStyles[signal as VolumeSignal];
  } else if (variant === "sentiment" && signal) {
    className = sentimentStyles[signal as SentimentSignal];
  } else if (variant === "status") {
    className = statusStyles[label.toLowerCase()] ?? "bg-muted/15 text-secondary";
  }

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${className}`}
    >
      {label}
    </span>
  );
}
