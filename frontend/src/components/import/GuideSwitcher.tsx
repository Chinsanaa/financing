'use client';

import { useEffect, useState } from 'react';

const ITEMS = [
  { id: 'alipay', label: 'Alipay' },
  { id: 'wechat', label: 'WeChat Pay' },
  { id: 'bank', label: 'Bank CSV' },
] as const;

/**
 * Sticky in-page switcher for /guide. Plain anchor links (work without JS);
 * after hydration an IntersectionObserver marks the section in view with
 * aria-current and the vermilion rule (the nav convention, see TabBar).
 */
export default function GuideSwitcher() {
  const [active, setActive] = useState<string>('alipay');

  useEffect(() => {
    if (typeof IntersectionObserver === 'undefined') return;
    const els = ITEMS.map((i) => document.getElementById(i.id)).filter(Boolean) as HTMLElement[];
    const obs = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) setActive(visible[0].target.id);
      },
      { rootMargin: '-30% 0px -60% 0px' }
    );
    els.forEach((el) => obs.observe(el));
    return () => obs.disconnect();
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
