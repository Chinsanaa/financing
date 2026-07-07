'use client';

import { InputHTMLAttributes, SelectHTMLAttributes, ReactNode } from 'react';

const FIELD_CLASSES =
  'w-full rounded-lg bg-surface-2 border border-edge/10 px-3.5 py-2.5 text-sm text-ink placeholder:text-muted outline-none transition-colors focus:border-accent/60 focus:ring-2 focus:ring-accent/20';

export default function Input({
  label,
  error,
  className = '',
  ...rest
}: InputHTMLAttributes<HTMLInputElement> & { label?: string; error?: string }) {
  return (
    <label className="block">
      {label && <span className="mb-1.5 block text-sm font-medium text-ink">{label}</span>}
      <input
        className={`${FIELD_CLASSES} ${error ? 'border-danger/60 focus:border-danger/60 focus:ring-danger/20' : ''} ${className}`}
        {...rest}
      />
      {error && <span className="mt-1 block text-xs text-danger">{error}</span>}
    </label>
  );
}

export function Select({
  label,
  children,
  className = '',
  ...rest
}: SelectHTMLAttributes<HTMLSelectElement> & { label?: string; children: ReactNode }) {
  return (
    <label className="block">
      {label && <span className="mb-1.5 block text-sm font-medium text-ink">{label}</span>}
      <select className={`${FIELD_CLASSES} ${className}`} {...rest}>
        {children}
      </select>
    </label>
  );
}
