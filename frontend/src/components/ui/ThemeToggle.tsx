'use client';

import { AnimatePresence, m } from 'framer-motion';
import { Moon, Sun } from 'lucide-react';
import Tooltip from './Tooltip';
import { toggleTheme, useIsDark } from '@/utils/theme';

export default function ThemeToggle() {
  const dark = useIsDark();
  const label = dark ? 'Switch to light theme' : 'Switch to dark theme';

  return (
    <Tooltip label={label}>
      <button
        onClick={toggleTheme}
        aria-label={label}
        className="flex h-11 w-11 items-center justify-center overflow-hidden rounded-pill border border-edge/10 text-muted transition-colors hover:text-ink hover:border-edge/25 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/40"
      >
        {/* Sun/moon swap: the outgoing icon spins down, the new one rises in. */}
        <AnimatePresence mode="wait" initial={false}>
          <m.span
            key={dark ? 'sun' : 'moon'}
            initial={{ y: 14, rotate: -90, opacity: 0 }}
            animate={{ y: 0, rotate: 0, opacity: 1 }}
            exit={{ y: -14, rotate: 90, opacity: 0 }}
            transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
            className="flex"
          >
            {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </m.span>
        </AnimatePresence>
      </button>
    </Tooltip>
  );
}
