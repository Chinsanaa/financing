'use client';

import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, m, PanInfo, useMotionValue, useReducedMotion, useTransform } from 'framer-motion';
import { Check, Keyboard } from 'lucide-react';
import { api } from '@/utils/api';
import { useApi, invalidate } from '@/utils/useApi';
import { advanceTour, useTour } from '@/utils/tour';
import { Alert, ProgressBar } from '@/components/ui-feedback';
import Button from '@/components/ui/Button';
import Card, { SectionHeader } from '@/components/ui/Card';
import Stamp from '@/components/ui/Stamp';
import Badge from '@/components/ui/Badge';
import { useCategoryColors } from '@/utils/useCategoryColors';
import EmptyState from '@/components/ui/EmptyState';
import Skeleton, { SkeletonCard } from '@/components/ui/Skeleton';
import { formatCurrency, formatDate } from '@/utils/format';

interface Transaction {
  id: string;
  date: string;
  merchant: string;
  description: string;
  amount: number;
  confidence: number;
  suggested_category: string | null;
}

interface Category {
  id: string;
  name: string;
}

/**
 * The draggable slip. Each slip owns its motion value — the leaving and the
 * arriving slip are both mounted for a moment, and must not share an x.
 * It follows the pointer 1:1 (rubber-banding past the edges), shows
 * "Accept →" / "← Set aside" as it travels, and leaves in the direction the
 * AnimatePresence `custom` gives it.
 */
function Slip({
  children,
  disabled,
  canAccept,
  onDragEnd,
}: {
  children: React.ReactNode;
  disabled: boolean;
  canAccept: boolean;
  onDragEnd: (e: unknown, info: PanInfo) => void;
}) {
  const x = useMotionValue(0);
  const acceptHint = useTransform(x, [24, 120], [0, 1]);
  const skipHint = useTransform(x, [-120, -24], [1, 0]);
  return (
    <m.div
      className="relative cursor-grab touch-pan-y active:cursor-grabbing"
      drag={disabled ? false : 'x'}
      dragConstraints={{ left: 0, right: 0 }}
      dragElastic={0.7}
      dragTransition={{ bounceStiffness: 500, bounceDamping: 40 }}
      onDragEnd={onDragEnd}
      style={{ x }}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0, rotate: 0 }}
      variants={{
        gone: (d: number) => ({ x: d * 380, rotate: d * 6, opacity: 0, transition: { duration: 0.28, ease: [0.55, 0, 1, 0.45] } }),
      }}
      exit="gone"
      transition={{ type: 'spring', bounce: 0, duration: 0.3 }}
    >
      <Card variant="raised" className="relative space-y-5 p-6 sm:p-7">
        {canAccept && (
          <m.span style={{ opacity: acceptHint }} aria-hidden="true" className="pointer-events-none absolute -top-6 right-1 text-xs font-medium text-accent-strong">
            Accept →
          </m.span>
        )}
        <m.span style={{ opacity: skipHint }} aria-hidden="true" className="pointer-events-none absolute -top-6 left-1 text-xs text-muted">
          ← Set aside
        </m.span>
        {children}
      </Card>
    </m.div>
  );
}

export default function LabelTab() {
  const queueQ = useApi<{ transactions: Transaction[] }>('/dashboard/review-queue');
  const categoriesQ = useApi<{ categories: Category[] }>('/categories/');
  const { toneFor, chartColorFor } = useCategoryColors();
  const [currentIndex, setCurrentIndex] = useState(0);
  const [acting, setActing] = useState(false);
  const [actionError, setActionError] = useState('');
  const [skippedIds, setSkippedIds] = useState<Set<string>>(new Set());
  // Progress is tracked separately from the (shrinking) `transactions` array:
  // totalCount is captured once from the first successful load and stays
  // fixed for the session, labeledCount only ever increases as items get
  // labeled — so the "X of Y" display and progress bar can only go up,
  // never regress as the local queue array shrinks.
  const [totalCount, setTotalCount] = useState<number | null>(null);
  const [labeledCount, setLabeledCount] = useState(0);
  // The stamp shown on the current slip just before it leaves, and which way
  // it leaves (+1 right = labeled, -1 left = set aside).
  const [stamp, setStamp] = useState<{ id: string; label: string } | null>(null);
  const [exitDir, setExitDir] = useState(1);
  const reduce = useReducedMotion();

  const transactions = queueQ.data?.transactions || [];
  const categories = categoriesQ.data?.categories || [];
  const allSeen = transactions.length > 0 && skippedIds.size === transactions.length;

  useEffect(() => {
    if (queueQ.data && totalCount === null) {
      setTotalCount(queueQ.data.transactions.length);
    }
  }, [queueQ.data, totalCount]);

  const removeCurrent = () => {
    const tx = transactions[currentIndex];
    queueQ.setData((prev) =>
      prev
        ? { ...prev, transactions: prev.transactions.filter((t) => t.id !== tx.id) }
        : prev
    );
    setCurrentIndex((i) => Math.min(i, Math.max(0, transactions.length - 2)));
    setLabeledCount((c) => c + 1);
    // Refresh stats/action counts, but not the review queue itself — its
    // local state above is already correct, and a background refetch here
    // would race the optimistic splice.
    invalidate('/dashboard', { except: ['/dashboard/review-queue'] });
  };

  /** Let the stamp land, then let the slip go. */
  const stampThenRemove = async (tx: Transaction, label: string) => {
    setExitDir(1);
    setStamp({ id: tx.id, label });
    if (!reduce) await new Promise((res) => setTimeout(res, 420));
    removeCurrent();
    setStamp(null);
  };

  const handleAccept = async () => {
    const tx = transactions[currentIndex];
    if (!tx) return;

    try {
      setActing(true);
      setActionError('');
      await api.classifyTx.accept(tx.id);
      await stampThenRemove(tx, tx.suggested_category || 'Labeled');
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Failed to accept classification');
    } finally {
      setActing(false);
    }
  };

  const handleOverride = async (categoryId: string) => {
    const tx = transactions[currentIndex];
    if (!tx) return;

    try {
      setActing(true);
      setActionError('');
      await api.classifyTx.label(tx.id, categoryId);
      await stampThenRemove(tx, categories.find((c) => c.id === categoryId)?.name || 'Labeled');
      advanceTour('label'); // a hand label (rule-labeled rows never count)
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Failed to label transaction');
    } finally {
      setActing(false);
    }
  };

  const handleSkip = () => {
    if (transactions.length === 0 || allSeen) return;
    const tx = transactions[currentIndex];
    setExitDir(-1);
    setSkippedIds((prev) => new Set(prev).add(tx.id));

    // Find next unskipped transaction
    let nextIndex = (currentIndex + 1) % transactions.length;
    while (nextIndex !== currentIndex && skippedIds.has(transactions[nextIndex].id)) {
      nextIndex = (nextIndex + 1) % transactions.length;
    }
    setCurrentIndex(nextIndex);
  };

  /** Apple-style release: project where the fling would come to rest
   *  (velocity × deceleration, apple-design §6) and decide from that, so a
   *  quick flick counts as much as a long drag. */
  const handleDragEnd = (_: unknown, info: PanInfo) => {
    const projected = info.offset.x + info.velocity.x * 0.099; // decel 0.99
    if (acting) return;
    if (projected > 160 && transactions[currentIndex]?.suggested_category) handleAccept();
    else if (projected < -160 && transactions.length > 1) handleSkip();
  };

  const handleResetSkipped = () => {
    setSkippedIds(new Set());
    setCurrentIndex(0);
  };

  // Keyboard shortcuts — 1–9 pick a category, Enter accepts the suggestion,
  // S skips. The ref always holds this render's handlers, so the single
  // listener never calls a stale closure.
  const keysRef = useRef({ handleAccept, handleOverride, handleSkip, categories, acting, allSeen, tx: transactions[currentIndex] });
  keysRef.current = { handleAccept, handleOverride, handleSkip, categories, acting, allSeen, tx: transactions[currentIndex] };
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const k = keysRef.current;
      const target = e.target as HTMLElement | null;
      if (
        e.metaKey || e.ctrlKey || e.altKey ||
        target?.closest('input, textarea, select, [contenteditable], [role="dialog"]')
      ) return;
      if (!k.tx || k.acting || k.allSeen) return;
      if (/^[1-9]$/.test(e.key)) {
        const cat = k.categories[Number(e.key) - 1];
        if (cat) {
          e.preventDefault();
          k.handleOverride(cat.id);
        }
      } else if (e.key === 'Enter' && k.tx.suggested_category && target?.tagName !== 'BUTTON') {
        e.preventDefault();
        k.handleAccept();
      } else if (e.key.toLowerCase() === 's') {
        e.preventDefault();
        k.handleSkip();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const tour = useTour();

  if (queueQ.loading || categoriesQ.loading) {
    return (
      <div className="w-full space-y-6">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-16 w-full" />
        <SkeletonCard />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  if (transactions.length === 0) {
    return (
      <div className="w-full" data-tour-id="label-area">
        <EmptyState
          icon={Check}
          title="All transactions labeled"
          description="Nothing left in the queue. Upload another statement or retrain your model with the new labels."
          action={
            // If rules already labeled everything there's nothing to hand-label,
            // so let the user move the tour on themselves (never automatic).
            tour?.step === 'label' ? (
              <Button onClick={() => advanceTour('label')}>Continue the tour</Button>
            ) : undefined
          }
        />
      </div>
    );
  }

  const tx = transactions[Math.min(currentIndex, transactions.length - 1)];
  const displayTotal = totalCount ?? transactions.length;
  const progress = displayTotal > 0 ? Math.round((labeledCount / displayTotal) * 100) : 0;

  const setAside = skippedIds.size;

  return (
    <div className="w-full space-y-6" data-tour-id="label-area">
      <SectionHeader
        title="Label transactions"
        description="Every label you set here becomes training data for your model."
      />

      {/* Progress as one ruled line, not a card */}
      <div>
        <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2 text-sm">
          <span>
            <span className="num text-lg">{labeledCount}</span>
            <span className="text-muted"> of {displayTotal} labeled this session</span>
          </span>
          {setAside > 0 && !allSeen && (
            <span className="text-[13px] text-muted">
              {setAside} set aside ·{' '}
              <button onClick={handleResetSkipped} className="text-ink underline decoration-edge/30 underline-offset-4 hover:decoration-accent">
                bring them back
              </button>
            </span>
          )}
        </div>
        <ProgressBar percent={progress} height="h-1" label="Labeling progress" />
      </div>

      {(actionError || queueQ.error) && <Alert kind="error">{actionError || queueQ.error}</Alert>}

      {/* Left: the slip + accept. Right: category keys. Stacks below lg. */}
      <div className="grid gap-8 lg:grid-cols-2 lg:items-start">
        <div className="space-y-4">
          <div className="relative">
            {/* The slip underneath, peeking — the queue has depth */}
            {transactions.length > 1 && (
              <div aria-hidden="true" className="absolute inset-x-4 -bottom-2 h-full rounded-card border border-edge/12 bg-surface" />
            )}
            <AnimatePresence mode="popLayout" custom={exitDir} initial={false}>
              <Slip key={tx.id} disabled={acting} canAccept={!!tx.suggested_category} onDragEnd={handleDragEnd}>
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <p className="text-[13px] text-muted">{formatDate(tx.date)}</p>
                      <p className="mt-1 font-display text-3xl leading-tight">{tx.merchant}</p>
                      {tx.description && tx.description !== tx.merchant && (
                        <p className="mt-1 text-sm text-muted">{tx.description}</p>
                      )}
                    </div>
                    <p className="num shrink-0 text-3xl">{formatCurrency(tx.amount)}</p>
                  </div>

                  <div className="flex min-h-[28px] flex-wrap items-center gap-x-3 gap-y-2 border-t border-edge/12 pt-4 text-sm">
                    {stamp?.id === tx.id ? (
                      <Stamp label={stamp.label} tilt={-3} />
                    ) : tx.suggested_category ? (
                      <>
                        <span className="text-muted">Your model suggests</span>
                        <Badge tone={toneFor(tx.suggested_category)} guess>
                          {tx.suggested_category}
                        </Badge>
                        {tx.confidence > 0 && (
                          <span className="num ml-auto text-[13px] text-muted">{Math.round(tx.confidence * 100)}% sure</span>
                        )}
                      </>
                    ) : (
                      <span className="text-muted">No suggestion yet — pick a category.</span>
                    )}
                  </div>
              </Slip>
            </AnimatePresence>
          </div>

          {!allSeen && tx.suggested_category && (
            <Button onClick={handleAccept} loading={acting} className="w-full" size="lg">
              <Check className="h-4 w-4" /> Accept {tx.suggested_category}
              <span className="kbd ml-1 border-accent-ink/25 bg-transparent text-accent-ink">Enter</span>
            </Button>
          )}
        </div>

        <div className="space-y-3">
          {allSeen ? (
            <div className="space-y-3 border-t border-ink/80 pt-4">
              <p className="font-display text-2xl">Everything has been seen</p>
              <p className="text-sm text-muted">
                You set aside all {transactions.length} remaining transactions. Bring them back to go through them again.
              </p>
              <Button variant="outline" onClick={handleResetSkipped}>
                Bring them back
              </Button>
            </div>
          ) : (
            <>
              <p className="text-[13px] text-muted">Or pick a category</p>
              <div className="grid grid-cols-2 gap-px overflow-hidden rounded-md border border-edge/15 bg-edge/15 sm:grid-cols-3">
                {categories.map((cat, i) => (
                  <button
                    key={cat.id}
                    onClick={() => handleOverride(cat.id)}
                    disabled={acting}
                    className="flex items-center gap-2 bg-bg px-3 py-2.5 text-left text-sm transition-colors duration-100 hover:bg-surface active:bg-surface-2 disabled:opacity-50"
                  >
                    <span className="h-2.5 w-2.5 shrink-0 rounded-[2px]" style={{ backgroundColor: chartColorFor(cat.name) }} aria-hidden="true" />
                    <span className="min-w-0 flex-1 truncate">{cat.name}</span>
                    {i < 9 && <span className="kbd hidden sm:inline-flex">{i + 1}</span>}
                  </button>
                ))}
              </div>

              {transactions.length > 1 && (
                <Button variant="ghost" onClick={handleSkip} className="w-full">
                  Set aside for now <span className="kbd">S</span>
                </Button>
              )}
              <p className="hidden items-center justify-center gap-1.5 text-xs text-muted sm:flex">
                <Keyboard className="h-3.5 w-3.5" aria-hidden="true" /> 1–9 picks a category · drag the slip right to accept, left to set aside
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
