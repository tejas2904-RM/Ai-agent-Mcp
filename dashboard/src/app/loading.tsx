export default function Loading() {
  return (
    <div className="min-h-screen bg-canvas">
      <div className="h-14 animate-pulse border-b border-border bg-surface" />
      <div className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6">
        <div className="h-10 w-2/3 animate-pulse rounded bg-border" />
        <div className="h-4 w-1/3 animate-pulse rounded bg-border" />
        <div className="grid gap-4 md:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-48 animate-pulse rounded-card bg-surface shadow-card" />
          ))}
        </div>
      </div>
    </div>
  );
}
