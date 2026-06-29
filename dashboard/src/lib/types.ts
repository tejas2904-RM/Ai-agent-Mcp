export type VolumeSignal = "high" | "medium" | "low";
export type SentimentSignal = "negative" | "mixed" | "positive";

export interface TopThemeInsight {
  rank: number;
  name: string;
  summary: string;
  volume_signal: VolumeSignal;
  sentiment_signal: SentimentSignal;
  severity_score: number;
  review_count: number;
  avg_rating: number;
  low_star_pct: number;
}

export interface TraceableQuote {
  text: string;
  review_id: number;
  theme_name: string;
  rating: number;
  source: string;
}

export interface ActionIdea {
  theme_name: string;
  idea: string;
}

export interface DeliveryLinks {
  document_url: string | null;
  draft_id: string | null;
}

export interface PulsePayload {
  week_range: string;
  title: string;
  note_content: string;
  word_count: number;
  top_themes: TopThemeInsight[];
  quotes: TraceableQuote[];
  action_ideas: ActionIdea[];
  delivery: DeliveryLinks;
  run_id: string | null;
  generated_at: string | null;
}

export interface WeekSummary {
  week_range: string;
  title: string;
  status?: string | null;
  run_id?: string | null;
  completed_at?: string | null;
  document_url?: string | null;
}

export interface RunSummary {
  run_id: string;
  week_range: string | null;
  status: string;
  started_at: string;
  completed_at: string | null;
  is_rerun: boolean;
  delivery_skipped: boolean;
  note_word_count: number | null;
  document_url: string | null;
  draft_id: string | null;
}
