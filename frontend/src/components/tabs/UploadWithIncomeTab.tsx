'use client';

import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { api } from '@/utils/api';
import { useApi, invalidate } from '@/utils/useApi';
import type { ProfileResponse } from '@/types/v5';
import Button from '@/components/ui/Button';
import { FIELD_CLASSES } from '@/components/ui/Input';
import Card from '@/components/ui/Card';
import { Alert } from '@/components/ui-feedback';
import UploadTab from './UploadTab';
import { CURRENCY_SYMBOL } from '@/utils/format';
import { errorDetail } from '@/utils/errors';

export default function UploadWithIncomeTab() {
  const [income, setIncome] = useState<string>('');
  const [savingIncome, setSavingIncome] = useState(false);
  const [incomeError, setIncomeError] = useState('');

  // Shares useApi's cache with Settings, so both always show the same value.
  const { data: profileData } = useApi<ProfileResponse>(api.paths.profile);
  const savedIncome = profileData?.profile?.monthly_income;
  // Prefill once the saved value arrives, without clobbering what's typed.
  useEffect(() => {
    if (savedIncome != null) setIncome((current) => current || savedIncome.toString());
  }, [savedIncome]);

  const handleSaveIncome = async () => {
    if (!income || parseFloat(income) <= 0) {
      setIncomeError('Please enter a valid income amount');
      return;
    }

    setSavingIncome(true);
    setIncomeError('');

    try {
      await api.settings.updateProfile({ monthly_income: parseFloat(income) });
      // Budget, Savings and 50/30/20 all derive from income: drop their
      // cached figures so the toast below is actually true.
      invalidate('/dashboard');
      invalidate(api.paths.profile);
      toast.success('Income saved', { description: 'Budgets and savings now use it.' });
    } catch (err: any) {
      setIncomeError(errorDetail(err, 'Failed to save income'));
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
              <label htmlFor="monthly-income" className="block text-sm font-medium text-ink mb-2">
                Income amount ({CURRENCY_SYMBOL})
              </label>
              <input
                id="monthly-income"
                type="number"
                inputMode="decimal"
                value={income}
                onChange={(e) => setIncome(e.target.value)}
                placeholder="e.g., 15000"
                className={`${FIELD_CLASSES} w-full py-2.5`}
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
