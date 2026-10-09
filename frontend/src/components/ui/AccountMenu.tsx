'use client';

import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, m } from 'framer-motion';
import { LogOut, Settings } from 'lucide-react';
import { setTheme, useIsDark } from '@/utils/theme';
import Segmented from './Segmented';

/**
 * One account menu instead of a row of icon buttons: who you are, Settings,
 * the theme as a plain Light / Dark choice (no sun/moon toggle), Sign out.
 */
export default function AccountMenu({ name, onSignOut }: { name: string; onSignOut: () => void }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const dark = useIsDark();

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const initial = (name || '?').charAt(0).toUpperCase();
  const item =
    'flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left text-sm text-ink transition-colors hover:bg-edge/[0.06]';

  return (
    <div ref={rootRef} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label="Account menu"
        aria-haspopup="menu"
        aria-expanded={open}
        className="flex h-10 items-center gap-2 rounded-md pl-1 pr-2 text-sm text-ink transition-colors hover:bg-edge/6 active:scale-[0.97]"
      >
        <span className="flex h-8 w-8 items-center justify-center rounded-md bg-ink font-display text-base text-bg">
          {initial}
        </span>
        <span className="hidden max-w-[10rem] truncate lg:inline">{name}</span>
      </button>

      <AnimatePresence>
        {open && (
          <m.div
            role="menu"
            initial={{ opacity: 0, scale: 0.97, y: -4 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.98, transition: { duration: 0.12 } }}
            transition={{ type: 'spring', bounce: 0, duration: 0.24 }}
            style={{ transformOrigin: 'top right' }}
            className="glass absolute right-0 top-full z-50 mt-2 w-64 rounded-card p-1.5 shadow-card"
          >
            <p className="truncate px-2.5 pb-2 pt-1.5 text-[13px] text-muted">Signed in as {name}</p>
            <Link href="/settings" role="menuitem" className={item} onClick={() => setOpen(false)}>
              <Settings className="h-4 w-4 text-muted" aria-hidden="true" /> Settings
            </Link>
            <div className="my-1.5 border-t border-edge/12" />
            <div className="flex items-center justify-between px-2.5 py-1.5">
              <span className="text-sm">Theme</span>
              <Segmented
                label="Theme"
                layoutId="theme-choice"
                size="sm"
                value={dark ? 'dark' : 'light'}
                onChange={setTheme}
                options={[
                  { value: 'light', label: 'Light' },
                  { value: 'dark', label: 'Dark' },
                ]}
              />
            </div>
            <div className="my-1.5 border-t border-edge/12" />
            <button role="menuitem" className={`${item} hover:text-danger`} onClick={onSignOut}>
              <LogOut className="h-4 w-4 text-muted" aria-hidden="true" /> Sign out
            </button>
          </m.div>
        )}
      </AnimatePresence>
    </div>
  );
}
