'use client';

import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Check, PartyPopper } from 'lucide-react';
import { api } from '@/utils/api';
import { useApi, invalidate } from '@/utils/useApi';
import { Alert, ProgressBar } from '@/components/ui';
import Button from '@/components/ui/Button';
import Card, { SectionHeader } from '@/components/ui/Card';
import Badge, { categoryColor } from '@/components/ui/Badge';
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
  const [currentIndex, setCurrentIndex] = useState(0);
  const [acting, setActing] = useState(false);
  const [actionError, setActionError] = useState('');
  const [skippedIds, setSkippedIds] = useState<Set<string>>(new Set());

  const transactions = queueQ.data?.transactions || [];
  const categories = categoriesQ.data?.categories || [];
  const allSeen = transactions.length > 0 && skippedIds.size === transactions.length;

  const removeCurrent = () => {
    const tx = transactions[currentIndex];
    queueQ.setData((prev) =>
      prev
        ? { ...prev, transactions: prev.transactions.filter((t) => t.id !== tx.id) }
        : prev
    );
    setCurrentIndex((i) => Math.min(i, Math.max(0, transactions.length - 2)));
    invalidate('/dashboard'); // stats/action counts changed
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

  if (queueQ.loading || categoriesQ.loading) {
    return (
      <div className="max-w-2xl space-y-6">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-16 w-full" />
        <SkeletonCard />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  if (transactions.length === 0) {
    return (
      <div className="max-w-2xl">
        <EmptyState
          icon={PartyPopper}
          title="All transactions labeled"
          description="Nothing left in the queue. Upload another statement or retrain your model with the new labels."
        />
      </div>
    );
  }

  const tx = transactions[Math.min(currentIndex, transactions.length - 1)];
  const progress = Math.round(((currentIndex + 1) / transactions.length) * 100);

  return (
    <div className="max-w-2xl space-y-6">
      <SectionHeader label="Transactions" title="Label transactions" />
      <p className="-mt-4 text-sm text-muted">
        Every label you set here becomes training data for your model.
      </p>

      <Card className="p-4">
        <div className="mb-2 flex items-center justify-between">
          <span className="section-label">Progress</span>
          <span className="text-sm text-muted tabular-nums">
            {currentIndex + 1} of {transactions.length}
          </span>
        </div>
        <ProgressBar percent={progress} />
      </Card>

      {(actionError || queueQ.error) && (
        <Alert kind="error">{actionError || queueQ.error}</Alert>
      )}

      <AnimatePresence mode="wait">
        <motion.div
          key={tx.id}
          initial={{ opacity: 0, x: 24 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -24 }}
          transition={{ duration: 0.2, ease: 'easeOut' }}
        >
          <Card className="space-y-4 p-6">
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
              <div className="flex items-center gap-2 rounded-lg border border-accent/25 bg-accent/5 px-4 py-3 text-sm">
                <span className="text-muted">Model suggests</span>
                <Badge tone={categoryColor(tx.suggested_category)}>
                  {tx.suggested_category}
                </Badge>
                {tx.confidence > 0 && (
                  <span className="text-muted">
                    {Math.round(tx.confidence * 100)}% confident
                  </span>
                )}
              </div>
            )}
          </Card>
        </motion.div>
      </AnimatePresence>

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
              </Button>
            )}

            <div>
              <p className="section-label mb-2">Or pick a category</p>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {categories.map((cat) => (
                  <button
                    key={cat.id}
                    onClick={() => handleOverride(cat.id)}
                    disabled={acting}
                    className="rounded-lg border border-edge/10 bg-surface px-3 py-2.5 text-sm font-medium transition-all hover:border-accent/40 hover:bg-accent/5 disabled:opacity-50"
                  >
                    {cat.name}
                  </button>
                ))}
              </div>
            </div>

            {transactions.length > 1 && (
              <Button variant="ghost" onClick={handleSkip} className="w-full">
                Skip for now
              </Button>
            )}
          </>
        )}
      </div>
    </div>
  );
}
