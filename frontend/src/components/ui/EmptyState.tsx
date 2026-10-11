import { ReactNode } from 'react';
import { LucideIcon } from 'lucide-react';

/**
 * "Nothing here yet": a quiet, left-aligned note — what will appear and how
 * to get it. No floating icon, no radiating ring; the icon (optional) sits
 * small and still beside the title.
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
    <div className="rounded-card border border-dashed border-edge/20 px-6 py-10">
      <h3 className="flex items-center gap-2 font-display text-xl font-medium">
        {Icon && <Icon className="h-4 w-4 text-muted" aria-hidden="true" />}
        {title}
      </h3>
      {description && <p className="mt-1.5 max-w-[52ch] text-sm text-muted">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
