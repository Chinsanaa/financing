import { ReactNode } from 'react';

/** Deterministic color for a category name so badges stay stable across renders. */
const PALETTE = [
  'text-accent-strong bg-accent/15',
  'text-violet bg-violet/15',
  'text-cyan bg-cyan/15',
  'text-success bg-success/15',
  'text-danger bg-danger/15',
];

export function categoryColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = (hash * 31 + name.charCodeAt(i)) | 0;
  return PALETTE[Math.abs(hash) % PALETTE.length];
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
