'use client';

import { motion } from 'framer-motion';
import Card from '@/components/ui/Card';
import Badge, { categoryColor } from '@/components/ui/Badge';

/** Decorative dashboard mockup for the hero: a glass card with an animated
 * spending line and a few category chips. Illustrative, not real data. */

const POINTS = '0,86 40,74 80,80 120,58 160,66 200,44 240,52 280,30 320,38 360,18';
const AREA = `0,110 ${POINTS} 360,110`;

const CHIPS = ['Food', 'Transport', 'Shopping', 'Rent', 'Fun'];

export default function HeroChart() {
  return (
    <Card glass className="p-6 shadow-card">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <p className="section-label">This month</p>
          <p className="font-display text-2xl font-bold">¥4,218.60</p>
        </div>
        <Badge tone="accent">-12% vs last month</Badge>
      </div>

      <svg viewBox="0 0 360 110" className="w-full" aria-hidden="true">
        <defs>
          <linearGradient id="hero-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgb(var(--accent))" stopOpacity="0.35" />
            <stop offset="100%" stopColor="rgb(var(--accent))" stopOpacity="0" />
          </linearGradient>
        </defs>
        {[0, 1, 2].map((i) => (
          <line
            key={i}
            x1="0"
            x2="360"
            y1={30 + i * 30}
            y2={30 + i * 30}
            stroke="rgb(var(--edge) / 0.08)"
            strokeWidth="1"
          />
        ))}
        <motion.polygon
          points={AREA}
          fill="url(#hero-fill)"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1.2, delay: 0.6 }}
        />
        <motion.polyline
          points={POINTS}
          fill="none"
          stroke="rgb(var(--accent))"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 1.4, ease: 'easeInOut', delay: 0.3 }}
        />
        <motion.circle
          cx="360"
          cy="18"
          r="4"
          fill="rgb(var(--accent))"
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 1.6, type: 'spring', stiffness: 400 }}
        />
      </svg>

      <div className="mt-5 flex flex-wrap gap-2">
        {CHIPS.map((c, i) => (
          <motion.span
            key={c}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.8 + i * 0.1 }}
          >
            <Badge tone={categoryColor(c)}>{c}</Badge>
          </motion.span>
        ))}
      </div>
    </Card>
  );
}
