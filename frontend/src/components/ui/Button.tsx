'use client';

import { ButtonHTMLAttributes, ReactNode } from 'react';
import { Loader2 } from 'lucide-react';

type Variant = 'primary' | 'ghost' | 'outline' | 'danger';
type Size = 'sm' | 'md' | 'lg';

const VARIANTS: Record<Variant, string> = {
  // btn-sheen: a light sweep crosses the button on hover (globals.css)
  primary:
    'btn-sheen bg-accent text-accent-ink font-semibold shadow-[0_1px_0_0_rgb(255_255_255/0.25)_inset] hover:shadow-glow active:scale-[0.97]',
  ghost: 'text-ink hover:bg-edge/5 active:scale-[0.97]',
  outline:
    'border border-edge/15 text-ink hover:border-accent/40 hover:bg-edge/5 active:scale-[0.97]',
  danger: 'bg-danger/10 text-danger hover:bg-danger/20 active:scale-[0.97]',
};

const SIZES: Record<Size, string> = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-sm',
  lg: 'px-6 py-3 text-base',
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
      className={`inline-flex items-center justify-center gap-2 rounded-pill transition-[transform,box-shadow,background-color,border-color,color] duration-150 ease-out disabled:opacity-50 disabled:pointer-events-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/40 ${VARIANTS[variant]} ${SIZES[size]} ${className}`}
      disabled={disabled || loading}
      {...rest}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
}
