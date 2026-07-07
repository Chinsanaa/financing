import { ReactNode } from 'react';
import { LucideIcon } from 'lucide-react';

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
    <div className="flex flex-col items-center justify-center rounded-card border border-dashed border-edge/15 bg-surface/50 px-6 py-14 text-center">
      {Icon && (
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-accent/10">
          <Icon className="h-6 w-6 text-accent-strong" />
        </div>
      )}
      <h3 className="font-display text-lg font-semibold">{title}</h3>
      {description && <p className="mt-1.5 max-w-sm text-sm text-muted">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
