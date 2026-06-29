import type { ActionIdea } from "@/lib/types";

interface ActionListProps {
  actions: ActionIdea[];
}

export function ActionList({ actions }: ActionListProps) {
  if (actions.length === 0) {
    return (
      <p className="text-sm text-muted">No action ideas for this week.</p>
    );
  }

  return (
    <ul className="space-y-3">
      {actions.map((action, index) => (
        <li
          key={`${action.theme_name}-${index}`}
          className="rounded-card border border-border bg-surface p-4 shadow-card"
        >
          <p className="text-xs font-medium text-primary">{action.theme_name}</p>
          <p className="mt-1 text-sm text-heading">{action.idea}</p>
        </li>
      ))}
    </ul>
  );
}
