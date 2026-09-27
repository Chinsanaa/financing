'use client';

import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, m } from 'framer-motion';
import { Check, Keyboard, PartyPopper } from 'lucide-react';
import { api } from '@/utils/api';
import { useApi, invalidate } from '@/utils/useApi';
import { Alert, ProgressBar } from '@/components/ui-feedback';
import Button from '@/components/ui/Button';
import Card, { SectionHeader } from '@/components/ui/Card';
import Badge from '@/components/ui/Badge';
import { useCategoryColors } from '@/utils/useCategoryColors';
import EmptyState from '@/components/ui/EmptyState';
import Skeleton, { SkeletonCard } from '@/components/ui/Skeleton';
import { formatCurrency } from '@/utils/format';

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

  const handleAccept = async () => {
    const tx = transactions[currentIndex];
    if (!tx) return;

    try {
      setActing(true);
      setActionError('');
      await api.classifyTx.accept(tx.id);
      removeCurrent();
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
      removeCurrent();
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Failed to label transaction');
    } finally {
      setActing(false);
    }
  };

  const handleSkip = () => {
    if (transactions.length === 0 || allSeen) return;
    const tx = transactions[currentIndex];
    setSkippedIds((prev) => new Set(prev).add(tx.id));

    // Find next unskipped transaction
    let nextIndex = (currentIndex + 1) % transactions.length;
    while (nextIndex !== currentIndex && skippedIds.has(transactions[nextIndex].id)) {
      nextIndex = (nextIndex + 1) % transactions.length;
    }
    setCurrentIndex(nextIndex);
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

  if (queueQ.loading || categoriesQ.loading) {
    return (
      <div className="mx-auto max-w-2xl space-y-6">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-16 w-full" />
        <SkeletonCard />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  if (transactions.length === 0) {
    return (
      <div className="mx-auto max-w-2xl">
        <EmptyState
          icon={PartyPopper}
          title="All transactions labeled"
          description="Nothing left in the queue. Upload another statement or retrain your model with the new labels."
        />
      </div>
    );
  }

  const tx = transactions[Math.min(currentIndex, transactions.length - 1)];
  const displayTotal = totalCount ?? transactions.length;
  const progress = displayTotal > 0 ? Math.round((labeledCount / displayTotal) * 100) : 0;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <SectionHeader label="Transactions" title="Label transactions" />
      <p className="-mt-4 text-sm text-muted">
        Every label you set here becomes training data for your model.
      </p>

      <Card className="p-4">
        <div className="mb-2 flex items-center justify-between">
          <span className="section-label">Progress</span>
          <span className="text-sm text-muted tabular-nums">
            {labeledCount} of {displayTotal}
          </span>
        </div>
        <ProgressBar percent={progress} />
      </Card>

      {(actionError || queueQ.error) && (
        <Alert kind="error">{actionError || queueQ.error}</Alert>
      )}

      {/* Stacked deck: two faux cards peek out behind the current one */}
      <div className="relative">
        {transactions.length > 1 && (
          <div aria-hidden="true" className="absolute inset-x-6 -bottom-2 h-full rounded-card border border-edge/8 bg-surface/60" />
        )}
        {transactions.length > 2 && (
          <div aria-hidden="true" className="absolute inset-x-12 -bottom-4 h-full rounded-card border border-edge/5 bg-surface/30" />
        )}
      <AnimatePresence mode="wait">
        <m.div
          key={tx.id}
          className="relative"
          initial={{ opacity: 0, y: 12, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, x: 60, rotate: 3, transition: { duration: 0.16, ease: [0.55, 0, 1, 0.45] } }}
          transition={{ duration: 0.24, ease: [0.22, 1, 0.36, 1] }}
        >
          <Card className="space-y-4 p-6 shadow-card">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="section-label mb-1">Merchant</p>
                <p className="font-medium">{tx.merchant}</p>
              </div>
              <div>
                <p className="section-label mb-1">Amount</p>
                <p className="font-display text-lg font-semibold tabular-nums">
                  {formatCurrency(tx.amount)}
                </p>
              </div>
            </div>

            <div>
              <p className="section-label mb-1">Description</p>
              <p className="text-sm text-muted">{tx.description}</p>
            </div>

            {tx.suggested_category && (
              <div className="flex flex-wrap items-center gap-x-3 gap-y-2 rounded-lg border border-accent/25 bg-accent/5 px-4 py-3 text-sm">
                <span className="text-muted">Model suggests</span>
                <Badge tone={toneFor(tx.suggested_category)}>
                  {tx.suggested_category}
                </Badge>
                {tx.confidence > 0 && (
                  <span className="ml-auto flex items-center gap-2 text-xs text-muted">
                    <span className="w-20">
                      <ProgressBar percent={tx.confidence * 100} height="h-1.5" label="Model confidence" />
                    </span>
                    <span className="tabular-nums">{Math.round(tx.confidence * 100)}% sure</span>
                  </span>
                )}
              </div>
            )}
          </Card>
        </m.div>
      </AnimatePresence>
      </div>

      <div className="space-y-3">
        {allSeen ? (
          <div className="flex flex-col gap-3">
            <div className="rounded-lg border border-accent/25 bg-accent/5 p-4">
              <p className="font-medium text-accent-strong mb-1">All reviewed</p>
              <p className="text-sm text-muted">
                You've reviewed all {transactions.length} transactions. Reset skipped to review again.
              </p>
            </div>
            <Button variant="outline" onClick={handleResetSkipped} className="w-full">
              Reset skipped
            </Button>
          </div>
        ) : (
          <>
            {tx.suggested_category && (
              <Button onClick={handleAccept} loading={acting} className="w-full" size="lg">
                <Check className="h-4 w-4" /> Accept suggestion
                <span className="ml-1 rounded border border-accent-ink/20 px-1.5 text-[11px] font-medium opacity-70">Enter</span>
              </Button>
            )}

            <div>
              <p className="section-label mb-2">Or pick a category</p>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {categories.map((cat, i) => (
                  <button
                    key={cat.id}
                    onClick={() => handleOverride(cat.id)}
                    disabled={acting}
                    className="group flex items-center gap-2 rounded-lg border border-edge/10 bg-surface px-3 py-2.5 text-left text-sm font-medium transition-all duration-150 hover:-translate-y-px hover:border-accent/40 hover:bg-accent/5 active:scale-[0.98] disabled:opacity-50"
                  >
                    <span
                      className="h-2.5 w-2.5 shrink-0 rounded-full transition-transform duration-200 group-hover:scale-125"
                      style={{ backgroundColor: chartColorFor(cat.name) }}
                    />
                    <span className="min-w-0 flex-1 truncate">{cat.name}</span>
                    {i < 9 && <span className="kbd hidden sm:inline-flex">{i + 1}</span>}
                  </button>
                ))}
              </div>
            </div>

            {transactions.length > 1 && (
              <Button variant="ghost" onClick={handleSkip} className="w-full">
                Skip for now <span className="kbd">S</span>
              </Button>
            )}
            <p className="hidden items-center justify-center gap-1.5 text-xs text-muted sm:flex">
              <Keyboard className="h-3.5 w-3.5" /> Tip: press 1–9 to pick a category without the mouse
            </p>
          </>
        )}
      </div>
    </div>
  );
}
