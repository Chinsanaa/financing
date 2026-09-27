'use client';

import { useEffect, useState } from 'react';

/** Flip light/dark (class on <html>) and persist the choice. */
export function toggleTheme() {
  const next = !document.documentElement.classList.contains('dark');
  document.documentElement.classList.toggle('dark', next);
  try {
    localStorage.setItem('theme', next ? 'dark' : 'light');
  } catch {
    /* storage unavailable — theme still applies for this page view */
  }
}

/** Live `isDark`, updated no matter who toggles the theme (button, ⌘K). */
export function useIsDark() {
  // Initial value must match the server render; real theme read after mount.
  const [dark, setDark] = useState(true);
  useEffect(() => {
    const root = document.documentElement;
    const sync = () => setDark(root.classList.contains('dark'));
    sync();
    const obs = new MutationObserver(sync);
    obs.observe(root, { attributes: true, attributeFilter: ['class'] });
    return () => obs.disconnect();
  }, []);
  return dark;
}
