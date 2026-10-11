'use client';

import { useEffect, useState } from 'react';

const ITEMS = [
  { id: 'alipay', label: 'Alipay' },
  { id: 'wechat', label: 'WeChat Pay' },
  { id: 'bank', label: 'Bank CSV' },
] as const;

/**
 * Sticky in-page switcher for /guide. Plain anchor links (work without JS);
 * after hydration a rAF-throttled scroll check marks the section in view with
 * aria-current and the vermilion rule (the nav convention, see TabBar).
 */
export default function GuideSwitcher() {
  const [active, setActive] = useState<string>('alipay');

  useEffect(() => {
    // Active = the last section whose top has passed 35% of the viewport
    // (deterministic for anchor jumps, unlike intersection ratios).
    let frame = 0;
    const update = () => {
      frame = 0;
      const line = window.innerHeight * 0.35;
      let current: string = ITEMS[0].id;
      for (const i of ITEMS) {
        const el = document.getElementById(i.id);
        if (el && el.getBoundingClientRect().top <= line) current = i.id;
      }
      setActive(current);
    };
    const onScroll = () => {
      if (!frame) frame = requestAnimationFrame(update);
    };
    update();
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
    return () => {
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onScroll);
      if (frame) cancelAnimationFrame(frame);
    };
  }, []);

  return (
    <nav aria-label="Choose a statement" className="sticky top-[57px] z-30 -mx-4 border-b border-edge/15 bg-bg px-4 sm:mx-0 sm:px-0">
      <ul className="flex gap-6">
        {ITEMS.map((i) => {
          const on = active === i.id;
          return (
            <li key={i.id}>
              <a
                href={`#${i.id}`}
                aria-current={on ? 'location' : undefined}
                onClick={() => setActive(i.id)}
                className={`-mb-px inline-block border-b-2 py-3 text-sm transition-colors duration-150 ${
                  on ? 'border-accent text-ink' : 'border-transparent text-muted hover:text-ink'
                }`}
              >
                {i.label}
              </a>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
