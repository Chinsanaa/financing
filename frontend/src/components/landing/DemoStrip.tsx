'use client';

import { useEffect, useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { Sparkles } from 'lucide-react';
import Card from '@/components/ui/Card';
import Badge, { categoryColor } from '@/components/ui/Badge';

/** Interactive demo: raw transactions arrive uncategorized, then the "model"
 * stamps a category on each one — a looping illustration of the product. */

const DEMO_ROWS = [
  { merchant: 'Luckin Coffee', note: 'Latte, WeChat Pay', amount: '¥19.00', category: 'Food' },
  { merchant: 'Didi Chuxing', note: 'Ride home, Alipay', amount: '¥23.50', category: 'Transport' },
  { merchant: 'Taobao', note: 'Desk lamp order', amount: '¥89.90', category: 'Shopping' },
  { merchant: 'Meituan', note: 'Dinner delivery', amount: '¥42.30', category: 'Food' },
];

export default function DemoStrip() {
  const reduce = useReducedMotion();
  const [labeled, setLabeled] = useState(0);

  useEffect(() => {
    if (reduce) {
      setLabeled(DEMO_ROWS.length);
      return;
    }
    const timer = setInterval(() => {
      setLabeled((n) => (n >= DEMO_ROWS.length ? 0 : n + 1));
    }, 1400);
    return () => clearInterval(timer);
  }, [reduce]);

  return (
    <Card glass className="overflow-hidden p-6">
      <div className="mb-4 flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-accent-strong" />
        <p className="section-label">Watch the model work</p>
      </div>
      <div className="space-y-2">
        {DEMO_ROWS.map((row, i) => {
          const done = i < labeled;
          return (
            <div
              key={row.merchant}
              className={`flex items-center justify-between gap-3 rounded-lg border px-4 py-3 transition-colors duration-500 ${
                done ? 'border-accent/25 bg-accent/5' : 'border-edge/8 bg-surface'
              }`}
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">{row.merchant}</p>
                <p className="truncate text-xs text-muted">{row.note}</p>
              </div>
              <div className="flex shrink-0 items-center gap-3">
                <AnimatePresence mode="wait">
                  {done ? (
                    <motion.span
                      key="badge"
                      initial={{ opacity: 0, scale: 0.7 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0 }}
                      transition={{ type: 'spring', stiffness: 400, damping: 25 }}
                    >
                      <Badge tone={categoryColor(row.category)}>{row.category}</Badge>
                    </motion.span>
                  ) : (
                    <motion.span
                      key="pending"
                      exit={{ opacity: 0 }}
                      className="text-xs text-muted"
                    >
                      Uncategorized
                    </motion.span>
                  )}
                </AnimatePresence>
                <span className="text-sm font-medium tabular-nums">{row.amount}</span>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
