'use client';

import { ReactNode } from 'react';
import { Lightbulb, PiggyBank } from 'lucide-react';
import { Alert, ProgressBar } from '@/components/ui-feedback';
import Card from '@/components/ui/Card';
import EmptyState from '@/components/ui/EmptyState';
import { SkeletonCard } from '@/components/ui/Skeleton';
import { useApi } from '@/utils/useApi';
import { chartColorForKey } from '@/utils/categoryColors';
import { formatCurrencyWhole } from '@/utils/format';

export interface BucketCategory {
  category: string;
  amount: number;
}

export interface Bucket {
  target_pct: number;
  target_amount: number | null;
  spent: number;
  categories: BucketCategory[];
}

export interface RuleData {
  month: string;
  available_months: string[];
  income: number;
  buckets: {
    needs: Bucket;
    wants: Bucket;
    savings: Bucket;
  };
}

// Fixed bucket colors — these are aggregate buckets, not per-category
// identities, so they stay constant rather than going through
// useCategoryColors(). Picked from the same design-system palette.
const BUCKET_COLOR: Record<'needs' | 'wants' | 'savings', string> = {
  needs: chartColorForKey('sky'),
  wants: chartColorForKey('amber'),
  savings: chartColorForKey('emerald'),
};

const BUCKET_LABEL: Record<'needs' | 'wants' | 'savings', string> = {
  needs: 'Needs',
  wants: 'Wants',
  savings: 'Savings & Investing',
};

const ADVICE_TOLERANCE_PCT = 3;

/** Fetches the 50/30/20 breakdown for a given month (empty string = current month). */
export function useRuleData(month: string) {
  return useApi<RuleData>(month ? `/dashboard/rule-503020?month=${month}` : '/dashboard/rule-503020');
}

/**
 * Needs/Wants/Savings: one income-wide bar + per-bucket actual-vs-target bars, plus a
 * guidance box. Shared between the standalone 50/30/20 tab and the Budget
 * tab, which both show this for the same selected month.
 */
export default function RuleBreakdown({
  data,
  loading,
  error,
  header,
}: {
  data?: RuleData | null;
  loading: boolean;
  error?: string | null;
  /** Optional content (e.g. a month selector row) rendered at the top of the chart card. */
  header?: ReactNode;
}) {
  const buckets = data?.buckets;
  const hasIncome = !!data && data.income > 0;
  const hasAnySpend =
    !!buckets && (buckets.needs.spent > 0 || buckets.wants.spent > 0 || buckets.savings.spent > 0);

  const pctOfIncome = (spent: number) => (hasIncome ? Math.round((spent / data!.income) * 100) : 0);

  const advice = (() => {
    if (!buckets || !hasIncome) return null;
    const needsPct = pctOfIncome(buckets.needs.spent);
    const wantsPct = pctOfIncome(buckets.wants.spent);
    const savingsPct = pctOfIncome(buckets.savings.spent);

    const onTrack =
      Math.abs(needsPct - 50) <= ADVICE_TOLERANCE_PCT &&
      Math.abs(wantsPct - 30) <= ADVICE_TOLERANCE_PCT &&
      Math.abs(savingsPct - 20) <= ADVICE_TOLERANCE_PCT;
    if (onTrack) {
      return { onTrack: true as const, text: "You're right on track with the 50/30/20 rule this month." };
    }

    // Prioritize a savings shortfall — that's the rule's aspirational goal —
    // then whichever spend bucket runs hottest over its target.
    if (savingsPct < 20 - ADVICE_TOLERANCE_PCT) {
      const topWant = buckets.wants.categories[0];
      const suggestion = topWant
        ? ` Trimming your largest "want" — ${topWant.category} — would free up more room to save.`
        : '';
      return {
        onTrack: false as const,
        text: `You're saving ${savingsPct}% of income (target 20%).${suggestion}`,
      };
    }
    if (needsPct > 50 + ADVICE_TOLERANCE_PCT) {
      const topNeed = buckets.needs.categories[0];
      const suggestion = topNeed ? ` Your biggest needs category is ${topNeed.category} — see if there's room to reduce it.` : '';
      return {
        onTrack: false as const,
        text: `You're spending ${needsPct}% of income on needs (target 50%).${suggestion}`,
      };
    }
    if (wantsPct > 30 + ADVICE_TOLERANCE_PCT) {
      const topWant = buckets.wants.categories[0];
      const suggestion = topWant ? ` Your biggest "want" is ${topWant.category} — consider cutting back there first.` : '';
      return {
        onTrack: false as const,
        text: `You're spending ${wantsPct}% of income on wants (target 30%).${suggestion}`,
      };
    }
    return { onTrack: true as const, text: "You're right on track with the 50/30/20 rule this month." };
  })();

  if (loading) {
    return <SkeletonCard />;
  }

  return (
    <div className="space-y-6">
      {error && <Alert kind="error">{error}</Alert>}

      {data && !hasIncome && (
        <Alert kind="info">
          Set your monthly income in Settings to see targets and personalized guidance — spend is still
          shown below.
        </Alert>
      )}

      <Card variant="plain" className="pt-4">
        {header}
        {!hasAnySpend ? (
          <EmptyState
            icon={PiggyBank}
            title="No spend yet this month"
            description="Categorize some transactions to see your Needs/Wants/Savings split."
          />
        ) : (
          <div className="space-y-8">
            {hasIncome && (
              // One bar = your income. Segments are what each bucket took;
              // the ticks are where the rule puts the 50 / 80 boundaries.
              <div>
                <div className="relative">
                  <div className="flex h-10 w-full gap-[2px] bg-edge/8" role="img" aria-label="Share of income by bucket">
                    {(['needs', 'wants', 'savings'] as const).map((key) => (
                      <span
                        key={key}
                        className="progress-fill h-full"
                        style={{ width: `${Math.min(pctOfIncome(buckets![key].spent), 100)}%`, backgroundColor: BUCKET_COLOR[key] }}
                      />
                    ))}
                  </div>
                  {[50, 80].map((t) => (
                    <span key={t} aria-hidden="true" className="absolute -bottom-1.5 -top-1.5 w-px bg-ink" style={{ left: `${t}%` }} />
                  ))}
                </div>
                <div className="relative mt-2 h-4 text-[11px] text-muted">
                  <span className="absolute left-0">0</span>
                  <span className="absolute -translate-x-1/2" style={{ left: '50%' }}>50% needs</span>
                  <span className="absolute -translate-x-1/2" style={{ left: '80%' }}>+30% wants</span>
                  <span className="absolute right-0">100% of income</span>
                </div>
              </div>
            )}
            <div className="space-y-6">
              {(['needs', 'wants', 'savings'] as const).map((key) => {
                const b = buckets![key];
                const actualPct = pctOfIncome(b.spent);
                return (
                  <div key={key}>
                    <div className="mb-1 flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <span
                          className="h-2.5 w-2.5 shrink-0 rounded-[2px]"
                          style={{ backgroundColor: BUCKET_COLOR[key] }}
                          aria-hidden="true"
                        />
                        <span className="text-sm font-medium">{BUCKET_LABEL[key]}</span>
                      </div>
                      <p className="text-[13px] text-muted">
                        <span className="num text-[15px] text-ink">{formatCurrencyWhole(b.spent)}</span>
                        {hasIncome && ` · ${actualPct}%`}
                        {b.target_amount !== null && ` of ${formatCurrencyWhole(b.target_amount)} (${b.target_pct}%) target`}
                      </p>
                    </div>
                    {/* Tick = the rule's target share (50/30/20) for this bucket */}
                    <ProgressBar
                      percent={hasIncome ? actualPct : 0}
                      fillColor={BUCKET_COLOR[key]}
                      marker={hasIncome ? b.target_pct : undefined}
                      label={`${BUCKET_LABEL[key]} share of income`}
                    />
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </Card>

      {advice && (
        <div
          className={`flex items-start gap-3 rounded-md border p-5 ${
            advice.onTrack ? 'border-success/25 bg-success/[0.06]' : 'border-warn/25 bg-warn/[0.06]'
          }`}
        >
          {!advice.onTrack && <Lightbulb className="mt-0.5 h-5 w-5 shrink-0 text-warn" aria-hidden="true" />}
          <div>
            <p className={`font-medium ${advice.onTrack ? 'text-success' : 'text-warn'}`}>
              {advice.onTrack ? 'On track' : 'Guidance'}
            </p>
            <p className="mt-0.5 text-sm text-muted">{advice.text}</p>
          </div>
        </div>
      )}
    </div>
  );
}
