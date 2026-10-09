'use client';

import { useEffect, useState } from 'react';

/** Apply light/dark (class on <html>) and persist the choice. */
export function setTheme(theme: 'light' | 'dark') {
  document.documentElement.classList.toggle('dark', theme === 'dark');
  try {
    localStorage.setItem('theme', theme);
  } catch {
    /* storage unavailable — theme still applies for this page view */
  }
}

/** Flip light/dark (⌘K command). */
export function toggleTheme() {
  setTheme(document.documentElement.classList.contains('dark') ? 'light' : 'dark');
}

/** Live `isDark`, updated no matter who changes the theme (menu, ⌘K). */
export function useIsDark() {
  // Initial value must match the server render (light); real theme read after mount.
  const [dark, setDark] = useState(false);
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
