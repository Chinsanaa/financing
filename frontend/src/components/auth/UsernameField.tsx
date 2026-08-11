'use client';

import { useEffect, useState } from 'react';
import { Check, X } from 'lucide-react';
import { createClient } from '@/utils/supabase';
import { useDebouncedValue } from '@/utils/useDebouncedValue';
import Input from '@/components/ui/Input';

const USERNAME_FORMAT = /^[a-zA-Z0-9_]{3,20}$/;

export default function UsernameField({
  value,
  onChange,
  onAvailabilityChange,
}: {
  value: string;
  onChange: (value: string) => void;
  /** Reports whether the current value is a confirmed-available username, so the parent form can gate submit. */
  onAvailabilityChange: (available: boolean) => void;
}) {
  const [supabase] = useState(() => createClient());
  const [checking, setChecking] = useState(false);
  const [available, setAvailable] = useState<boolean | null>(null);
  const debounced = useDebouncedValue(value, 400);

  useEffect(() => {
    if (!debounced || !USERNAME_FORMAT.test(debounced)) {
      setAvailable(null);
      onAvailabilityChange(false);
      return;
    }

    let cancelled = false;
    setChecking(true);

    (async () => {
      const { data, error } = await supabase.rpc('is_username_available', {
        check_username: debounced,
      });
      if (cancelled) return;
      const isAvailable = !error && data === true;
      setAvailable(isAvailable);
      onAvailabilityChange(isAvailable);
      setChecking(false);
    })();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debounced, supabase]);

  const formatError =
    value.length > 0 && !USERNAME_FORMAT.test(value)
      ? '3-20 characters: letters, numbers, underscore'
      : undefined;

  return (
    <div>
      <Input
        label="Username"
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value.trim())}
        required
        placeholder="yourusername"
        autoComplete="username"
        error={formatError}
      />
      {!formatError && value.length > 0 && (
        <p
          className={`mt-1.5 flex items-center gap-1.5 text-xs ${
            checking
              ? 'text-muted'
              : available
              ? 'text-success'
              : available === false
              ? 'text-danger'
              : 'text-muted'
          }`}
        >
          {checking ? (
            'Checking availability…'
          ) : available ? (
            <>
              <Check className="h-3.5 w-3.5" /> Username is available
            </>
          ) : available === false ? (
            <>
              <X className="h-3.5 w-3.5" /> Username is taken
            </>
          ) : null}
        </p>
      )}
    </div>
  );
}
