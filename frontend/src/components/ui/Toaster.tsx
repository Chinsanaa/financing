'use client';

import { Toaster as Sonner } from 'sonner';
import { useIsDark } from '@/utils/theme';

/**
 * App-wide toast host (sonner). Follows our class-based theme (not the OS
 * setting) by watching <html class="dark">. Use `toast.success(...)` from
 * 'sonner' for confirmations of completed actions; keep errors inline
 * next to the thing that failed (<Alert kind="error">).
 */
export default function Toaster() {
  const theme = useIsDark() ? 'dark' : 'light';
  return (
    <Sonner
      theme={theme}
      position="bottom-right"
      closeButton
      toastOptions={{
        classNames: {
          toast: '!rounded-card !border-edge/15 !bg-surface !text-ink !shadow-card !font-sans',
          description: '!text-muted',
          success: '[&_[data-icon]]:!text-success',
          error: '[&_[data-icon]]:!text-danger',
        },
      }}
    />
  );
}
