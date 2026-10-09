'use client';

import { ButtonHTMLAttributes, ReactNode } from 'react';
import { Loader2 } from 'lucide-react';

type Variant = 'primary' | 'ghost' | 'outline' | 'danger' | 'link';
type Size = 'sm' | 'md' | 'lg';

// Feedback lives on the press, and it's instant (apple-design: respond on
// pointer-down). Exits/hover settle in 150ms.
const PRESS = 'active:scale-[0.97] active:duration-75';

const VARIANTS: Record<Variant, string> = {
  primary: `bg-accent text-accent-ink font-medium hover:bg-accent-strong ${PRESS}`,
  ghost: `text-ink hover:bg-edge/6 ${PRESS}`,
  outline: `border border-edge/20 text-ink hover:border-edge/40 hover:bg-edge/[0.04] ${PRESS}`,
  danger: `border border-danger/30 text-danger hover:bg-danger/8 ${PRESS}`,
  // Tertiary action: plain underlined text, no box.
  link: 'px-0 py-0 text-ink underline decoration-edge/30 underline-offset-4 hover:decoration-accent',
};

const SIZES: Record<Size, string> = {
  sm: 'h-8 px-3 text-[13px]',
  md: 'h-10 px-4 text-sm',
  lg: 'h-12 px-5 text-[15px]',
};

export default function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  children,
  className = '',
  disabled,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  children: ReactNode;
}) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-md transition-[transform,background-color,border-color,color,text-decoration-color] duration-150 ease-out disabled:opacity-45 disabled:pointer-events-none ${VARIANTS[variant]} ${
        variant === 'link' ? '' : SIZES[size]
      } ${className}`}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
      {children}
    </button>
  );
}
