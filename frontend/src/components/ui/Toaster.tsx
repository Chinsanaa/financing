'use client';

import { useEffect, useState } from 'react';
import { Toaster as Sonner } from 'sonner';

/**
 * App-wide toast host (sonner). Follows our class-based theme (not the OS
 * setting) by watching <html class="dark">. Use `toast.success(...)` from
 * 'sonner' for confirmations of completed actions; keep errors inline
 * next to the thing that failed (<Alert kind="error">).
 */
export default function Toaster() {
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  useEffect(() => {
    const root = document.documentElement;
    const sync = () => setTheme(root.classList.contains('dark') ? 'dark' : 'light');
    sync();
    const obs = new MutationObserver(sync);
    obs.observe(root, { attributes: true, attributeFilter: ['class'] });
    return () => obs.disconnect();
  }, []);
  return (
    <Sonner
      theme={theme}
      position="bottom-right"
      closeButton
      toastOptions={{
        classNames: {
          toast: '!rounded-card !border-edge/10 !bg-surface !text-ink !shadow-card !font-sans',
          description: '!text-muted',
          success: '[&_[data-icon]]:!text-success',
          error: '[&_[data-icon]]:!text-danger',
        },
      }}
    />
  );
}
