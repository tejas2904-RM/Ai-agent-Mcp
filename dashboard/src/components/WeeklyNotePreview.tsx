interface WeeklyNotePreviewProps {
  content: string;
  wordCount: number;
}

export function WeeklyNotePreview({ content, wordCount }: WeeklyNotePreviewProps) {
  return (
    <section className="rounded-card border border-border bg-surface p-6 shadow-card">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-heading">Weekly Note Preview</h2>
        <span className="text-xs text-muted">{wordCount} words</span>
      </div>
      <div className="max-h-80 overflow-y-auto whitespace-pre-wrap text-sm leading-relaxed text-secondary">
        {content}
      </div>
    </section>
  );
}
