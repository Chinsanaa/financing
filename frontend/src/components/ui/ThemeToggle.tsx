'use client';

import { useEffect, useState } from 'react';
import { Moon, Sun } from 'lucide-react';
import Tooltip from './Tooltip';

export default function ThemeToggle() {
  // Initial value must match the server render; real theme applied after mount.
  const [dark, setDark] = useState(true);

  useEffect(() => {
    setDark(document.documentElement.classList.contains('dark'));
  }, []);

  const toggle = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle('dark', next);
    localStorage.setItem('theme', next ? 'dark' : 'light');
  };

  const label = dark ? 'Switch to light theme' : 'Switch to dark theme';

  return (
    <Tooltip label={label}>
      <button
        onClick={toggle}
        aria-label={label}
        className="flex h-11 w-11 items-center justify-center rounded-pill border border-edge/10 text-muted transition-colors hover:text-ink hover:border-edge/25 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/40"
      >
        {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
      </button>
    </Tooltip>
  );
}
