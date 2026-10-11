'use client';

import { InputHTMLAttributes, SelectHTMLAttributes, ReactNode, useId } from 'react';

/** Shared text-field look (also used by auth/PasswordInput). No width or vertical
 *  padding — callers add `w-full py-2.5` / `w-32 py-1.5` (Tailwind emits the larger
 *  step later, so a value here would silently override the caller's). */
export const FIELD_CLASSES =
  'rounded-md bg-surface border border-edge/20 px-3 text-sm text-ink placeholder:text-muted outline-none transition-colors hover:border-edge/35 focus:border-accent focus:ring-1 focus:ring-accent focus-visible:outline-none';

export default function Input({
  label,
  error,
  className = '',
  ...rest
}: InputHTMLAttributes<HTMLInputElement> & { label?: string; error?: string }) {
  const errorId = useId();
  return (
    <label className="block">
      {label && <span className="mb-1.5 block text-sm font-medium text-ink">{label}</span>}
      <input
        className={`${FIELD_CLASSES} w-full py-2.5 ${error ? 'border-danger focus:border-danger focus:ring-danger' : ''} ${className}`}
        aria-invalid={!!error}
        aria-describedby={error ? errorId : undefined}
        {...rest}
      />
      {error && (
        <span id={errorId} role="alert" className="mt-1 block text-xs text-danger">
          {error}
        </span>
      )}
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
      <select className={`${FIELD_CLASSES} w-full py-2.5 ${className}`} {...rest}>
        {children}
      </select>
    </label>
  );
}
