import type { ReactNode } from 'react';

/**
 * A flat, abstract phone used to illustrate one export step on /guide.
 *
 * Not a screenshot: solid token fills, a hairline body, short English labels
 * and one vermilion outline marking what to tap. Everything is drawn in a
 * fixed 120 × 220 coordinate space; the primitives below place themselves
 * inside the screen (x 12–108, y 30–206).
 *
 * THE RULE (docs/DESIGN_SYSTEM.md): solid colors only, no shadows on the
 * frame, solid fills only. Colors come from tokens (fill-surface, stroke-ink/…)
 * so light and dark follow the theme.
 */
export default function PhoneFrame({
  label,
  children,
  className = '',
}: {
  /** What the screen shows, for screen readers ("Alipay Me tab, Bills highlighted"). */
  label: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <svg
      viewBox="0 0 120 220"
      role="img"
      aria-label={label}
      textRendering="geometricPrecision"
      style={{ letterSpacing: 0, fontKerning: 'normal' }}
      className={`h-auto w-[108px] shrink-0 select-none font-sans sm:w-[124px] ${className}`}
    >
      {/* body */}
      <rect x="1" y="1" width="118" height="218" rx="17" className="fill-surface stroke-ink/40" strokeWidth="1.25" />
      {/* screen */}
      <rect x="6" y="6" width="108" height="208" rx="12" className="fill-bg" />
      {/* speaker slot */}
      <rect x="47" y="10" width="26" height="4" rx="2" className="fill-ink/15" />
      {children}
    </svg>
  );
}

/** Screen title bar (y 22–40) with optional left/right affordances. */
export function NavBar({
  title,
  right,
  back = false,
  rightHighlight = false,
}: {
  title: string;
  right?: string;
  back?: boolean;
  rightHighlight?: boolean;
}) {
  return (
    <g>
      {back && <path d="M17 27 l-4 4 l4 4" className="fill-none stroke-ink/60" strokeWidth="1.3" />}
      <text x="60" y="34" textAnchor="middle" fontSize="8" fontWeight="600" className="fill-ink">
        {title}
      </text>
      {right && (
        <>
          <text x="101" y="34" textAnchor="end" fontSize="8" fontWeight="600" className="fill-ink">
            {right}
          </text>
          {rightHighlight && <Highlight x={104 - (right.length * 4.6 + 6)} y={24} w={right.length * 4.6 + 6} h={14} />}
        </>
      )}
      <line x1="6" y1="42" x2="114" y2="42" className="stroke-ink/10" strokeWidth="0.75" />
    </g>
  );
}

/** A tappable list row. Without a label it is an abstract grey line. */
export function Row({
  y,
  label,
  hint,
  highlight = false,
  chevron = true,
}: {
  y: number;
  label?: string;
  hint?: string;
  highlight?: boolean;
  chevron?: boolean;
}) {
  return (
    <g>
      <rect x="12" y={y} width="96" height="18" rx="3" className="fill-surface" />
      {label ? (
        <text x="18" y={y + 11.6} fontSize="7" fontWeight={highlight ? 600 : 400} className="fill-ink">
          {label}
        </text>
      ) : (
        <rect x="18" y={y + 7.5} width="44" height="3" rx="1.5" className="fill-ink/15" />
      )}
      {hint && (
        <text x="18" y={y + 24} fontSize="5.5" className="fill-muted">
          {hint}
        </text>
      )}
      {chevron && <path d={`M100 ${y + 6} l3 3 l-3 3`} className="fill-none stroke-ink/35" strokeWidth="1" />}
      {highlight && <Highlight x={10} y={y - 2} w={100} h={22} />}
    </g>
  );
}

/** Abstract content lines (amounts, merchants) — deliberately unreadable. */
export function Lines({ y, count = 3, gap = 14 }: { y: number; count?: number; gap?: number }) {
  return (
    <g>
      {Array.from({ length: count }, (_, i) => (
        <g key={i}>
          <rect x="14" y={y + i * gap} width={i % 2 ? 40 : 52} height="3" rx="1.5" className="fill-ink/15" />
          <rect x="84" y={y + i * gap} width="22" height="3" rx="1.5" className="fill-ink/25" />
        </g>
      ))}
    </g>
  );
}

/** Bottom tab bar; `active` is the index drawn in ink, `highlight` gets the marker. */
export function TabBar({ items, active, highlight }: { items: string[]; active?: number; highlight?: number }) {
  const w = 108 / items.length;
  return (
    <g>
      <line x1="6" y1="190" x2="114" y2="190" className="stroke-ink/10" strokeWidth="0.75" />
      {items.map((it, i) => {
        const cx = 6 + w * i + w / 2;
        const on = i === active || i === highlight;
        return (
          <g key={it}>
            <rect x={cx - 4} y="194" width="8" height="6" rx="1.5" className={on ? 'fill-ink' : 'fill-ink/20'} />
            <text x={cx} y="208" textAnchor="middle" fontSize="5.5" fontWeight={on ? 600 : 400} className={on ? 'fill-ink' : 'fill-muted'}>
              {it}
            </text>
            {i === highlight && <Highlight x={cx - w / 2 + 2} y={191} w={w - 4} h={21} />}
          </g>
        );
      })}
    </g>
  );
}

/** A bottom sheet of options (the "···" menu), one of them highlighted. */
export function Sheet({ options, highlight, title }: { options: string[]; highlight?: number; title?: string }) {
  const rowH = 17;
  const top = 206 - options.length * rowH - (title ? 14 : 4);
  return (
    <g>
      {/* dimmed page behind the sheet: a flat ink wash */}
      <rect x="6" y="43" width="108" height="171" className="fill-ink/10" />
      <rect x="6" y={top} width="108" height={214 - top} rx="10" className="fill-surface stroke-ink/15" strokeWidth="0.75" />
      {title && (
        <text x="60" y={top + 11} textAnchor="middle" fontSize="6" className="fill-muted">
          {title}
        </text>
      )}
      {options.map((o, i) => {
        const y = top + (title ? 14 : 4) + i * rowH;
        return (
          <g key={o}>
            {i > 0 && <line x1="14" y1={y} x2="106" y2={y} className="stroke-ink/10" strokeWidth="0.6" />}
            <text x="60" y={y + 11} textAnchor="middle" fontSize="6.5" fontWeight={i === highlight ? 600 : 400} className="fill-ink">
              {o}
            </text>
            {i === highlight && <Highlight x={10} y={y + 1} w={100} h={rowH - 2} />}
          </g>
        );
      })}
    </g>
  );
}

/** An input field with a label above it. */
export function Field({ y, label, value }: { y: number; label: string; value?: string }) {
  return (
    <g>
      <text x="14" y={y} fontSize="5.5" className="fill-muted">
        {label}
      </text>
      <rect x="12" y={y + 3} width="96" height="14" rx="3" className="fill-surface stroke-ink/20" strokeWidth="0.75" />
      {value && (
        <text x="17" y={y + 12.5} fontSize="6.5" className="fill-ink">
          {value}
        </text>
      )}
    </g>
  );
}

/** A full-width button; `primary` is the vermilion fill (the step's target). */
export function ScreenButton({ y, label, primary = false }: { y: number; label: string; primary?: boolean }) {
  return (
    <g>
      <rect
        x="12"
        y={y}
        width="96"
        height="16"
        rx="4"
        className={primary ? 'fill-accent' : 'fill-surface stroke-ink/25'}
        strokeWidth="0.75"
      />
      <text
        x="60"
        y={y + 10.5}
        textAnchor="middle"
        fontSize="6.5"
        fontWeight="600"
        className={primary ? 'fill-accent-ink' : 'fill-ink'}
      >
        {label}
      </text>
    </g>
  );
}

/** A choice (radio) row; `selected` draws the dot, `highlight` the marker. */
export function Choice({ y, label, selected = false, highlight = false }: { y: number; label: string; selected?: boolean; highlight?: boolean }) {
  return (
    <g>
      <rect x="12" y={y} width="96" height="18" rx="3" className="fill-surface" />
      <circle cx="20" cy={y + 9} r="3.2" className="fill-none stroke-ink/50" strokeWidth="0.9" />
      {selected && <circle cx="20" cy={y + 9} r="1.7" className="fill-ink" />}
      <text x="27" y={y + 11.4} fontSize="5.8" fontWeight={selected ? 600 : 400} className="fill-ink">
        {label}
      </text>
      {highlight && <Highlight x={10} y={y - 2} w={100} h={22} />}
    </g>
  );
}

/** An email "inbox" card with an attachment chip. */
export function MailCard({ y, from, subject, attachment }: { y: number; from: string; subject: string; attachment: string }) {
  return (
    <g>
      <rect x="12" y={y} width="96" height="58" rx="4" className="fill-surface stroke-ink/15" strokeWidth="0.75" />
      <text x="18" y={y + 12} fontSize="6.5" fontWeight="600" className="fill-ink">
        {from}
      </text>
      <text x="18" y={y + 22} fontSize="5.5" className="fill-muted">
        {subject}
      </text>
      <rect x="18" y={y + 32} width="84" height="18" rx="3" className="fill-bg stroke-ink/20" strokeWidth="0.75" />
      <rect x="23" y={y + 36} width="8" height="10" rx="1" className="fill-ink/25" />
      <text x="35" y={y + 43.5} fontSize="6" fontWeight="600" className="fill-ink">
        {attachment}
      </text>
      <Highlight x={16} y={y + 30} w={88} h={22} />
    </g>
  );
}

/** A short message bubble (where the unzip password arrives). */
export function Notice({ y, title, body }: { y: number; title: string; body: string }) {
  return (
    <g>
      <rect x="12" y={y} width="96" height="34" rx="4" className="fill-surface stroke-ink/15" strokeWidth="0.75" />
      <text x="18" y={y + 12} fontSize="6" fontWeight="600" className="fill-ink">
        {title}
      </text>
      <text x="18" y={y + 24} fontSize="6" className="fill-muted">
        {body}
      </text>
    </g>
  );
}

/** The "tap here" marker: a vermilion outline (no fill, no glow). */
export function Highlight({ x, y, w, h }: { x: number; y: number; w: number; h: number }) {
  return <rect x={x} y={y} width={w} height={h} rx="4" className="fill-none stroke-accent" strokeWidth="1.6" />;
}
