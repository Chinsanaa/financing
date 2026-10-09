'use client';

import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { api } from '@/utils/api';
import Button from '@/components/ui/Button';
import { FIELD_CLASSES } from '@/components/ui/Input';
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
    // The income card sits beside the dropzone (right column) on wide screens.
    <UploadTab
      aside={
        <Card className="p-6">
          <h3 className="mb-2 font-display text-xl font-normal text-ink">
            Monthly income <span className="font-sans text-sm text-muted">(optional)</span>
          </h3>
          <p className="mb-4 text-sm text-muted">
            Enter your monthly income to enable budget tracking and savings calculations.
          </p>

          <div className="flex gap-3 items-end">
            <div className="flex-1">
              <label className="block text-sm font-medium text-ink mb-2">
                Income amount ({CURRENCY_SYMBOL})
              </label>
              <input
                type="number"
                value={income}
                onChange={(e) => setIncome(e.target.value)}
                placeholder="e.g., 15000"
                className={FIELD_CLASSES}
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
      }
    />
  );
}
