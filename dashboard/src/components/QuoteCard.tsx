import type { TraceableQuote } from "@/lib/types";

interface QuoteCardProps {
  quote: TraceableQuote;
}

export function QuoteCard({ quote }: QuoteCardProps) {
  return (
    <blockquote className="rounded-card border border-border bg-surface p-4 shadow-card">
      <p className="text-sm italic leading-relaxed text-heading">&ldquo;{quote.text}&rdquo;</p>
      <footer className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted">
        <span className="font-medium text-secondary">{quote.theme_name}</span>
        <span>·</span>
        <span>{quote.rating}★</span>
        <span>·</span>
        <span className="capitalize">{quote.source}</span>
        <span>·</span>
        <span>#{quote.review_id}</span>
      </footer>
    </blockquote>
  );
}
