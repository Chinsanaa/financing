'use client';

import { useState } from 'react';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import { Select } from '@/components/ui/Input';
import { Alert } from '@/components/ui-feedback';
import { formatCurrencyWhole } from '@/utils/format';

interface Category {
  id: string;
  name: string;
}

interface SplitLine {
  category_id: string;
  amount: string; // kept as string while editing, parsed on submit
}

interface SplitModalTxn {
  id: string;
  amount: number;
  is_split: boolean;
  splits?: { category_id: string; category_name: string; amount: number }[] | null;
}

interface SplitModalProps {
  transaction: SplitModalTxn;
  categories: Category[];
  saving: boolean;
  error: string;
  onSubmit: (splits: { category_id: string; amount: number }[]) => void;
  onUnsplit: () => void;
  onClose: () => void;
}

export default function SplitModal({
  transaction,
  categories,
  saving,
  error,
  onSubmit,
  onUnsplit,
  onClose,
}: SplitModalProps) {
  const initialLines: SplitLine[] =
    transaction.splits && transaction.splits.length > 0
      ? transaction.splits.map((s) => ({ category_id: s.category_id, amount: String(s.amount) }))
      : [
          { category_id: '', amount: '' },
          { category_id: '', amount: '' },
        ];
  const [lines, setLines] = useState<SplitLine[]>(initialLines);

  const setLine = (idx: number, patch: Partial<SplitLine>) => {
    setLines((prev) => prev.map((l, i) => (i === idx ? { ...l, ...patch } : l)));
  };

  const addLine = () => setLines((prev) => [...prev, { category_id: '', amount: '' }]);
  const removeLine = (idx: number) => setLines((prev) => prev.filter((_, i) => i !== idx));

  const total = lines.reduce((sum, l) => sum + (parseFloat(l.amount) || 0), 0);
  const mismatch = Math.abs(total - transaction.amount) >= 0.01;
  const incomplete = lines.length < 2 || lines.some((l) => !l.category_id || !l.amount);

  const handleSubmit = () => {
    if (mismatch || incomplete) return;
    onSubmit(lines.map((l) => ({ category_id: l.category_id, amount: parseFloat(l.amount) })));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <Card className="w-full max-w-md space-y-4 p-5">
        <h3 className="text-sm font-semibold">Split transaction</h3>

        <div className="space-y-2">
          {lines.map((line, idx) => (
            <div key={idx} className="flex items-center gap-2">
              <div className="w-[200px]">
                <Select
                  value={line.category_id}
                  onChange={(e) => setLine(idx, { category_id: e.target.value })}
                >
                  <option value="" disabled>
                    Category…
                  </option>
                  {categories.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </Select>
              </div>
              <input
                type="number"
                step="0.01"
                value={line.amount}
                onChange={(e) => setLine(idx, { amount: e.target.value })}
                placeholder="Amount"
                className="w-[110px] rounded-pill border border-edge/20 bg-surface px-3 py-1.5 text-sm text-ink focus:border-accent-strong/50 focus:outline-none focus:ring-2 focus:ring-accent/20"
              />
              {lines.length > 2 && (
                <Button variant="ghost" size="sm" onClick={() => removeLine(idx)}>
                  Remove
                </Button>
              )}
            </div>
          ))}
        </div>

        <Button variant="outline" size="sm" onClick={addLine}>
          Add category
        </Button>

        <p className={`text-sm ${mismatch ? 'text-red-500' : 'text-muted'}`}>
          Total: {formatCurrencyWhole(total)} / {formatCurrencyWhole(transaction.amount)}
        </p>

        {error && <Alert kind="error">{error}</Alert>}

        <div className="flex flex-wrap items-center justify-between gap-2 pt-2">
          <div className="flex gap-2">
            <Button onClick={handleSubmit} loading={saving} disabled={mismatch || incomplete || saving}>
              Save split
            </Button>
            <Button variant="ghost" onClick={onClose} disabled={saving}>
              Cancel
            </Button>
          </div>
          {transaction.is_split && (
            <Button variant="outline" onClick={onUnsplit} disabled={saving}>
              Remove split
            </Button>
          )}
        </div>
      </Card>
    </div>
  );
}
