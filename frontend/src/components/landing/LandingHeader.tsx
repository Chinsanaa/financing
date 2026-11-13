'use client';

import { type ReactNode, useEffect, useState } from 'react';

/** Fixed header shell: its bottom rule appears once the page has scrolled. */
export default function LandingHeader({ children }: { children: ReactNode }) {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <header
      className={`fixed inset-x-0 top-0 z-50 border-b bg-bg transition-[border-color] duration-200 ${
        scrolled ? 'border-edge/15' : 'border-transparent'
      }`}
    >
      {children}
    </header>
  );
}
