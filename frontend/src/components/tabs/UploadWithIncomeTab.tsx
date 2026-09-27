'use client';

import { useState, useEffect } from 'react';
import { Banknote } from 'lucide-react';
import { toast } from 'sonner';
import { api } from '@/utils/api';
import Button from '@/components/ui/Button';
import Card, { SectionHeader } from '@/components/ui/Card';
import { Alert } from '@/components/ui-feedback';
import UploadTab from './UploadTab';
import { CURRENCY_SYMBOL } from '@/utils/format';

export default function UploadWithIncomeTab() {
  const [income, setIncome] = useState<string>('');
  const [savingIncome, setSavingIncome] = useState(false);
  const [incomeError, setIncomeError] = useState('');

  // Fetch current income on mount
  useEffect(() => {
    const fetchIncome = async () => {
      try {
        const res = await api.get('/settings/profile');
        const monthlyIncome = res.data?.profile?.monthly_income;
        if (monthlyIncome != null) {
          setIncome(monthlyIncome.toString());
        }
      } catch (err) {
        console.error('Failed to fetch income:', err);
      }
    };
    fetchIncome();
  }, []);

  const handleSaveIncome = async () => {
    if (!income || parseFloat(income) <= 0) {
      setIncomeError('Please enter a valid income amount');
      return;
    }

    setSavingIncome(true);
    setIncomeError('');

    try {
      await api.patch('/settings/profile', {
        monthly_income: parseFloat(income),
      });
      toast.success('Income saved', { description: 'Budgets and savings now use it.' });
    } catch (err: any) {
      setIncomeError(err.response?.data?.detail || 'Failed to save income');
    } finally {
      setSavingIncome(false);
    }
  };

  return (
    // Same width as the nested UploadTab so the income card and upload panel align.
    <div className="mx-auto w-full max-w-2xl space-y-6">
      {/* Income Input Card */}
      <Card className="p-6">
        <div className="mb-3 flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent/12 text-accent-strong">
            <Banknote className="h-[18px] w-[18px]" />
          </span>
          <h3 className="font-display font-semibold text-ink">
            Monthly income <span className="font-sans text-sm font-normal text-muted">(optional)</span>
          </h3>
        </div>
        <p className="text-sm text-muted mb-4">
          Enter your monthly income to enable budget tracking and savings calculations.
        </p>

        <div className="flex gap-3 items-end">
          <div className="flex-1">
            <label className="block text-sm font-medium text-ink mb-2">
              Income Amount ({CURRENCY_SYMBOL})
            </label>
            <input
              type="number"
              value={income}
              onChange={(e) => setIncome(e.target.value)}
              placeholder="e.g., 15000"
              className="w-full rounded-pill border border-edge/15 bg-surface-2 px-4 py-2 text-ink placeholder-muted transition-colors focus:border-accent/60 focus:outline-none focus:ring-2 focus:ring-accent/20"
            />
          </div>
          <Button
            onClick={handleSaveIncome}
            loading={savingIncome}
            disabled={!income || savingIncome}
            variant="primary"
          >
            Save
          </Button>
        </div>

        {incomeError && <Alert kind="error">{incomeError}</Alert>}
      </Card>

      {/* Original Upload Tab */}
      <UploadTab />
    </div>
  );
}
