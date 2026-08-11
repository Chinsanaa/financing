'use client';

import { useId, useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';

const FIELD_CLASSES =
  'w-full rounded-lg bg-surface-2 border border-edge/10 pl-3.5 pr-10 py-2.5 text-sm text-ink placeholder:text-muted outline-none transition-colors focus:border-accent/60 focus:ring-2 focus:ring-accent/20';

export default function PasswordInput({
  label,
  value,
  onChange,
  error,
  placeholder,
  autoComplete,
  required,
}: {
  label: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  error?: string;
  placeholder?: string;
  autoComplete?: string;
  required?: boolean;
}) {
  const [visible, setVisible] = useState(false);
  const errorId = useId();

  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-ink">{label}</span>
      <div className="relative">
        <input
          type={visible ? 'text' : 'password'}
          value={value}
          onChange={onChange}
          required={required}
          placeholder={placeholder}
          autoComplete={autoComplete}
          aria-invalid={!!error}
          aria-describedby={error ? errorId : undefined}
          className={`${FIELD_CLASSES} ${error ? 'border-danger/60 focus:border-danger/60 focus:ring-danger/20' : ''}`}
        />
        <button
          type="button"
          tabIndex={-1}
          onClick={() => setVisible((v) => !v)}
          aria-label={visible ? 'Hide password' : 'Show password'}
          className="absolute inset-y-0 right-0 flex items-center pr-3 text-muted transition-colors hover:text-ink"
        >
          {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>
      {error && (
        <span id={errorId} role="alert" className="mt-1 block text-xs text-danger">
          {error}
        </span>
      )}
    </label>
  );
}
