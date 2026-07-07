'use client';

import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { CheckCircle2 } from 'lucide-react';
import { api } from '@/utils/api';
import { useApi, invalidate } from '@/utils/useApi';
import { Alert } from '@/components/ui';
import Card, { SectionHeader } from '@/components/ui/Card';
import Badge, { categoryColor } from '@/components/ui/Badge';
import EmptyState from '@/components/ui/EmptyState';
import Skeleton, { SkeletonRows } from '@/components/ui/Skeleton';

interface Transaction {
  id: string;
  date: string;
  merchant: string;
  description: string;
  amount: number;
  confidence: number;
  suggested_category: string | null;
  category?: string | null;
}

interface ReviewQueueData {
  transactions: Transaction[];
  count: number;
  type?: string;
}

export default function ReviewTab() {
  const [showLabeled, setShowLabeled] = useState(false);
  const queryString = showLabeled ? '?show_labeled=true' : '';
  const { data, setData, loading, error: loadError } = useApi<ReviewQueueData>(`/dashboard/review-queue${queryString}`);
  const categoriesQ = useApi<{ categories: Array<{ id: string; name: string }> }>('/categories/');
  const [selectedTxn, setSelectedTxn] = useState<string | null>(null);
  const [labeling, setLabeling] = useState<string | null>(null);
  const [actionError, setActionError] = useState('');

  const categories = categoriesQ.data?.categories || [];

  // Optimistically remove the acted-on row instead of refetching the whole
  // queue after every single action.
  const removeRow = (txnId: string) => {
    setData((prev) =>
      prev
        ? {
            ...prev,
            transactions: prev.transactions.filter((t) => t.id !== txnId),
            count: Math.max(0, prev.count - 1),
          }
        : prev
    );
    invalidate('/dashboard'); // stats/action counts changed
  };

  const handleLabel = async (txnId: string, categoryId: string) => {
    try {
      setLabeling(txnId);
      setActionError('');
      await api.classifyTx.label(txnId, categoryId);
      removeRow(txnId);
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Failed to label transaction');
    } finally {
      setLabeling(null);
    }
  };

  const handleAccept = async (txnId: string) => {
    try {
      setLabeling(txnId);
      setActionError('');
      await api.classifyTx.accept(txnId);
      removeRow(txnId);
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Failed to accept classification');
    } finally {
      setLabeling(null);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <SkeletonRows rows={7} />
      </div>
    );
  }

  const error = actionError || loadError;

  const isShowingLabeled = showLabeled;
  const title = isShowingLabeled ? 'Your labels' : 'Review queue';
  const description = isShowingLabeled
    ? 'Your manually labeled transactions. Review them to catch any human errors before retraining.'
    : 'Low-confidence classifications waiting for your call.';

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <SectionHeader label="Transactions" title={title} />
          <p className="-mt-4 text-sm text-muted">
            {description}
            {data && <span className="ml-1 tabular-nums">{data.count} items.</span>}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowLabeled(false)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
              !isShowingLabeled
                ? 'bg-accent/20 text-accent-strong'
                : 'bg-surface-2 text-muted hover:bg-surface-3'
            }`}
          >
            Model Suggestions
          </button>
          <button
            onClick={() => setShowLabeled(true)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
              isShowingLabeled
                ? 'bg-accent/20 text-accent-strong'
                : 'bg-surface-2 text-muted hover:bg-surface-3'
            }`}
          >
            My Labels
          </button>
        </div>
      </div>

      {error && <Alert kind="error">{error}</Alert>}

      {!data || data.transactions.length === 0 ? (
        <EmptyState
          icon={CheckCircle2}
          title={isShowingLabeled ? 'No labeled transactions' : 'No pending reviews'}
          description={
            isShowingLabeled
              ? 'Label some transactions first, then come back here to review them.'
              : 'All transactions are categorized. The queue refills when the model is unsure about new data.'
          }
        />
      ) : (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-edge/8 bg-surface-2/60">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-muted">Date</th>
                  <th className="px-4 py-3 text-left font-medium text-muted">Merchant</th>
                  <th className="px-4 py-3 text-left font-medium text-muted">Description</th>
                  <th className="px-4 py-3 text-right font-medium text-muted">Amount</th>
                  <th className="px-4 py-3 text-left font-medium text-muted">
                    {isShowingLabeled ? 'Your Category' : 'Suggestion'}
                  </th>
                  {!isShowingLabeled && (
                    <th className="px-4 py-3 text-center font-medium text-muted">Confidence</th>
                  )}
                  <th className="px-4 py-3 text-center font-medium text-muted">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-edge/8">
                <AnimatePresence initial={false}>
                  {data.transactions.map((tx) => (
                    <motion.tr
                      key={tx.id}
                      layout
                      exit={{ opacity: 0, x: -32 }}
                      transition={{ duration: 0.2 }}
                      className={`transition-colors hover:bg-edge/5 ${
                        selectedTxn === tx.id ? 'bg-accent/5' : ''
                      }`}
                    >
                      <td className="whitespace-nowrap px-4 py-3 text-xs text-muted">
                        {new Date(tx.date).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-3 font-medium">{tx.merchant}</td>
                      <td className="max-w-xs truncate px-4 py-3 text-xs text-muted">
                        {tx.description}
                      </td>
                      <td className="px-4 py-3 text-right font-medium tabular-nums">
                        ¥{tx.amount.toFixed(2)}
                      </td>
                      <td className="px-4 py-3">
                        {isShowingLabeled ? (
                          tx.category ? (
                            <Badge tone={categoryColor(tx.category)}>
                              {tx.category}
                            </Badge>
                          ) : (
                            <span className="text-xs text-muted">Uncategorized</span>
                          )
                        ) : tx.suggested_category ? (
                          <Badge tone={categoryColor(tx.suggested_category)}>
                            {tx.suggested_category}
                          </Badge>
                        ) : (
                          <span className="text-xs text-muted">No suggestion</span>
                        )}
                      </td>
                      {!isShowingLabeled && (
                        <td className="px-4 py-3 text-center text-xs text-muted tabular-nums">
                          {tx.confidence > 0 ? `${Math.round(tx.confidence * 100)}%` : '—'}
                        </td>
                      )}
                      <td className="px-4 py-3 text-center">
                        {selectedTxn === tx.id ? (
                          <div className="space-y-1.5">
                            {tx.suggested_category && (
                              <button
                                onClick={() => handleAccept(tx.id)}
                                disabled={labeling === tx.id}
                                className="block w-full rounded-lg bg-success/15 px-2 py-1.5 text-xs font-medium text-success transition-colors hover:bg-success/25 disabled:opacity-50"
                              >
                                {labeling === tx.id ? 'Labeling' : 'Accept'}
                              </button>
                            )}
                            <select
                              value=""
                              onChange={(e) => {
                                if (e.target.value) {
                                  handleLabel(tx.id, e.target.value);
                                }
                              }}
                              disabled={labeling === tx.id}
                              className="block w-full rounded-lg border border-edge/10 bg-surface-2 px-2 py-1.5 text-xs text-ink outline-none focus:border-accent/60"
                            >
                              <option value="">Change category</option>
                              {categories.map((cat) => (
                                <option key={cat.id} value={cat.id}>
                                  {cat.name}
                                </option>
                              ))}
                            </select>
                          </div>
                        ) : (
                          <button
                            onClick={() => setSelectedTxn(tx.id)}
                            className="text-xs font-medium text-accent-strong transition-colors hover:underline"
                          >
                            Review
                          </button>
                        )}
                      </td>
                    </motion.tr>
                  ))}
                </AnimatePresence>
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
