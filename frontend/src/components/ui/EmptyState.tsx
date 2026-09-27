import { ReactNode } from 'react';
import { LucideIcon } from 'lucide-react';

/**
 * Friendly "nothing here yet" panel: a floating icon with a soft radiating
 * ring. Always say what will appear and how to
 * get it (description / action).
 */
export default function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="relative flex flex-col items-center justify-center overflow-hidden rounded-card border border-dashed border-edge/15 bg-surface/50 px-6 py-14 text-center">
      {Icon && (
        <div className="relative mb-5 animate-float">
          <span className="absolute inset-0 rounded-2xl bg-accent/20 animate-ping-soft" aria-hidden="true" />
          <div className="relative flex h-14 w-14 items-center justify-center rounded-2xl border border-accent/25 bg-accent/10">
            <Icon className="h-6 w-6 text-accent-strong" />
          </div>
        </div>
      )}
      <h3 className="relative font-display text-lg font-semibold">{title}</h3>
      {description && <p className="relative mt-1.5 max-w-sm text-sm text-muted">{description}</p>}
      {action && <div className="relative mt-5">{action}</div>}
    </div>
  );
}
