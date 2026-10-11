import { FileSpreadsheet } from 'lucide-react';
import AlipayLogo from './AlipayLogo';
import WeChatPayLogo from './WeChatPayLogo';

/**
 * "Accepted formats" row: Alipay · WeChat Pay · Bank CSV.
 *
 * Brand-mark rules (docs/DESIGN_SYSTEM.md §5): the marks appear ONLY next to
 * accepted-formats text like this, unmodified, at their official colors, and
 * the text label is always visible beside each mark (the logo is never the
 * only label — so the marks themselves are aria-hidden here).
 */
export default function FormatBadges({
  size = 16,
  compact = false,
  variant = 'color',
  className = '',
}: {
  /** Logo height in px. */
  size?: number;
  /** Tighter gaps and 12px text (e.g. inside a drop zone). */
  compact?: boolean;
  /** `mono` paints both marks in currentColor (muted ink). */
  variant?: 'color' | 'mono';
  className?: string;
}) {
  const item = `inline-flex items-center ${compact ? 'gap-1.5' : 'gap-2'}`;
  const sep = (
    <span aria-hidden className="text-muted/60">
      ·
    </span>
  );
  return (
    <ul
      aria-label="Accepted formats"
      className={`flex flex-wrap items-center text-muted ${
        compact ? 'gap-x-2 gap-y-1 text-xs' : 'gap-x-3 gap-y-1.5 text-[13px]'
      } ${className}`}
    >
      <li className={item}>
        <AlipayLogo size={size} variant={variant} decorative />
        <span className="text-ink">Alipay</span>
      </li>
      <li aria-hidden className="contents">
        {sep}
      </li>
      <li className={item}>
        <WeChatPayLogo size={size} variant={variant} decorative />
        <span className="text-ink">WeChat Pay</span>
      </li>
      <li aria-hidden className="contents">
        {sep}
      </li>
      <li className={item}>
        <FileSpreadsheet aria-hidden width={size} height={size} strokeWidth={1.75} className="shrink-0 text-muted" />
        <span className="text-ink">Bank CSV</span>
      </li>
    </ul>
  );
}
