'use client';

import { useState, useEffect } from 'react';
import { DollarSign } from 'lucide-react';
import { api } from '@/utils/api';
import Button from '@/components/ui/Button';
import Card, { SectionHeader } from '@/components/ui/Card';
import { Alert } from '@/components/ui';
import UploadTab from './UploadTab';

export default function UploadWithIncomeTab() {
  const [income, setIncome] = useState<string>('');
  const [savingIncome, setSavingIncome] = useState(false);
  const [incomeError, setIncomeError] = useState('');
  const [incomeMessage, setIncomeMessage] = useState('');

  // Fetch current income on mount
  useEffect(() => {
    const fetchIncome = async () => {
      try {
        const res = await api.get('/settings/profile');
        if (res.data?.monthly_income) {
          setIncome(res.data.monthly_income.toString());
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
    setIncomeMessage('');

    try {
      await api.patch('/settings/profile', {
        monthly_income: parseFloat(income),
      });
      setIncomeMessage('Income saved successfully!');
      setTimeout(() => setIncomeMessage(''), 3000);
    } catch (err: any) {
      setIncomeError(err.response?.data?.detail || 'Failed to save income');
    } finally {
      setSavingIncome(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Income Input Card */}
      <Card className="border border-accent-strong/20 bg-accent-strong/5 p-6">
        <div className="flex items-center gap-3 mb-4">
          <DollarSign className="h-5 w-5 text-accent-strong" />
          <h3 className="font-semibold text-ink">Monthly Income (Optional)</h3>
        </div>
        <p className="text-sm text-muted mb-4">
          Enter your monthly income to enable budget tracking and savings calculations.
        </p>

        <div className="flex gap-3 items-end">
          <div className="flex-1">
            <label className="block text-sm font-medium text-ink mb-2">
              Income Amount (¥)
            </label>
            <input
              type="number"
              value={income}
              onChange={(e) => setIncome(e.target.value)}
              placeholder="e.g., 15000"
              className="w-full px-4 py-2 rounded-pill border border-edge/20 bg-surface text-ink placeholder-muted focus:outline-none focus:border-accent-strong/50 focus:ring-2 focus:ring-accent-strong/10"
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
        {incomeMessage && <Alert kind="success">{incomeMessage}</Alert>}
      </Card>

      {/* Original Upload Tab */}
      <UploadTab />
    </div>
  );
}
