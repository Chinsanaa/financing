import { ReactNode } from 'react';

/**
 * Ledger badge.
 * - Category (`tone` = a `cat-*` class): a small square swatch + the name in
 *   ink. The color identifies; the word carries the meaning.
 *   `guess` draws the swatch as an OUTLINE — the model's suggestion, not yet
 *   confirmed. Solid = confirmed. (State by line form, not by hue.)
 * - Status tones (`accent` / `success` / `danger` / `neutral`): a quiet
 *   tinted label with squared corners.
 */
export default function Badge({
  children,
  tone,
  guess = false,
  className = '',
}: {
  children: ReactNode;
  tone?: 'accent' | 'neutral' | 'success' | 'danger' | 'warn' | string;
  guess?: boolean;
  className?: string;
}) {
  const status: Record<string, string> = {
    accent: 'text-accent-strong bg-accent/10',
    success: 'text-success bg-success/12',
    danger: 'text-danger bg-danger/12',
    warn: 'text-warn bg-warn/12',
    neutral: 'text-muted bg-edge/8',
  };
  if (!tone || status[tone]) {
    return (
      <span
        className={`inline-flex items-center rounded-[4px] px-1.5 py-0.5 text-xs font-medium whitespace-nowrap ${
          status[tone || 'neutral']
        } ${className}`}
      >
        {children}
      </span>
    );
  }
  return (
    <span className={`inline-flex items-center gap-1.5 text-[13px] whitespace-nowrap text-ink ${tone} ${className}`}>
      <span
        aria-hidden="true"
        className="h-2.5 w-2.5 shrink-0 rounded-[2px]"
        style={
          guess
            ? { border: '1.5px solid rgb(var(--cat))' }
            : { backgroundColor: 'rgb(var(--cat))' }
        }
      />
      {children}
      {guess && <span className="sr-only"> (suggested)</span>}
    </span>
  );
}
