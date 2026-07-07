'use client';

import Link from 'next/link';
import { useRef, useState } from 'react';
import Button from '@/components/ui/Button';
import { ArrowLeft } from 'lucide-react';

export default function NotFound() {
  const ref = useRef<HTMLDivElement>(null);
  const [offset, setOffset] = useState({ x: 0, y: 0 });

  // Subtle parallax: the giant 404 drifts a few pixels toward the cursor.
  const onMove = (e: React.MouseEvent) => {
    const rect = ref.current?.getBoundingClientRect();
    if (!rect) return;
    setOffset({
      x: ((e.clientX - rect.left) / rect.width - 0.5) * 16,
      y: ((e.clientY - rect.top) / rect.height - 0.5) * 16,
    });
  };

  return (
    <div
      ref={ref}
      onMouseMove={onMove}
      className="bg-grid relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-4 text-center"
    >
      <div className="pointer-events-none absolute -top-32 left-1/2 h-96 w-[640px] -translate-x-1/2 rounded-full bg-violet/12 blur-3xl" />
      <p
        className="font-display select-none text-[10rem] font-bold leading-none tracking-tight text-edge/10 transition-transform duration-200 ease-out sm:text-[16rem]"
        style={{ transform: `translate(${offset.x}px, ${offset.y}px)` }}
        aria-hidden="true"
      >
        404
      </p>
      <div className="relative -mt-10 animate-fade-up sm:-mt-16">
        <p className="section-label mb-2">Page not found</p>
        <h1 className="font-display text-2xl font-bold tracking-tight sm:text-3xl">
          This transaction doesn&apos;t exist.
        </h1>
        <p className="mx-auto mt-2 max-w-sm text-sm text-muted">
          The page you&apos;re looking for was moved, deleted, or never categorized.
        </p>
        <div className="mt-6 flex justify-center gap-3">
          <Link href="/dashboard">
            <Button>
              <ArrowLeft className="h-4 w-4" /> Back to dashboard
            </Button>
          </Link>
          <Link href="/">
            <Button variant="outline">Go home</Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
