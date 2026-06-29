import type { TopThemeInsight } from "@/lib/types";
import { Pill } from "./Pill";

interface ThemeCardProps {
  theme: TopThemeInsight;
}

export function ThemeCard({ theme }: ThemeCardProps) {
  return (
    <article className="flex flex-col rounded-card border border-border bg-surface p-5 shadow-card">
      <div className="mb-3 flex items-start justify-between gap-2">
        <span className="text-xs font-medium text-muted">#{theme.rank}</span>
        <div className="flex flex-wrap gap-1.5">
          <Pill label={theme.volume_signal} variant="volume" signal={theme.volume_signal} />
          <Pill
            label={theme.sentiment_signal}
            variant="sentiment"
            signal={theme.sentiment_signal}
          />
        </div>
      </div>
      <h3 className="text-base font-semibold text-heading">{theme.name}</h3>
      <p className="mt-2 flex-1 text-sm leading-relaxed text-secondary">{theme.summary}</p>
      <dl className="mt-4 grid grid-cols-3 gap-2 border-t border-border pt-4 text-center">
        <div>
          <dt className="text-xs text-muted">Reviews</dt>
          <dd className="text-sm font-semibold text-heading">{theme.review_count}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted">Avg rating</dt>
          <dd className="text-sm font-semibold text-heading">{theme.avg_rating.toFixed(1)}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted">Low ★ %</dt>
          <dd className="text-sm font-semibold text-heading">
            {Math.round(theme.low_star_pct)}%
          </dd>
        </div>
      </dl>
    </article>
  );
}
