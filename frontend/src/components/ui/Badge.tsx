import { ReactNode } from 'react';
import { hashCategoryKey, toneForKey } from '@/utils/categoryColors';

/**
 * Deterministic fallback tone for a category name (stable across renders).
 * Components with access to the user's saved colors should prefer
 * `useCategoryColors().toneFor(name)` — this hash is for static contexts
 * (landing demos) and categories with no chosen color.
 */
export function categoryColor(name: string): string {
  return toneForKey(hashCategoryKey(name));
}

export default function Badge({
  children,
  tone,
  className = '',
}: {
  children: ReactNode;
  /** Explicit tone, or pass a category name via `category` semantics using categoryColor. */
  tone?: 'accent' | 'neutral' | 'success' | 'danger' | string;
  className?: string;
}) {
  const toneClass =
    tone === 'accent'
      ? 'text-accent-strong bg-accent/15'
      : tone === 'success'
      ? 'text-success bg-success/15'
      : tone === 'danger'
      ? 'text-danger bg-danger/15'
      : tone === 'neutral' || !tone
      ? 'text-muted bg-edge/8'
      : tone; // raw class string from categoryColor()
  return (
    <span
      className={`inline-flex items-center rounded-pill px-2.5 py-0.5 text-xs font-medium whitespace-nowrap ${toneClass} ${className}`}
    >
      {children}
    </span>
  );
}
