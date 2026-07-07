'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  ChartPie,
  FileText,
  LayoutDashboard,
  LogOut,
  Settings,
  Workflow,
} from 'lucide-react';
import { createClient } from '@/utils/supabase';
import { TabBar, TabPanel, TabItem } from '@/components/ui/Tabs';
import ThemeToggle from '@/components/ui/ThemeToggle';
import DashboardLoading from './loading';
import OnboardingChecklist from '@/components/onboarding/OnboardingChecklist';
import StatsTab from '@/components/tabs/StatsTab';
import BudgetTab from '@/components/tabs/BudgetTab';
import SavingsTab from '@/components/tabs/SavingsTab';
import ActionTab from '@/components/tabs/ActionTab';
import ReportsTab from '@/components/tabs/ReportsTab';
import TransactionsModelTab from '@/components/tabs/TransactionsModelTab';

/** Four sections with sub-tabs. Transactions & Model merged into one workflow. */
const SECTIONS: (TabItem & { subs: TabItem[] })[] = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard, subs: [] },
  {
    id: 'transactions-model',
    label: 'Transactions & Model',
    icon: Workflow,
    subs: [],
  },
  {
    id: 'planning',
    label: 'Planning',
    icon: ChartPie,
    subs: [
      { id: 'budget', label: 'Budget' },
      { id: 'savings', label: 'Savings' },
      { id: 'action', label: 'Action plan' },
    ],
  },
  { id: 'reports', label: 'Reports', icon: FileText, subs: [] },
];

/** Tab id → its section (for ActionTab's onNavigate and URL params). */
const TAB_SECTION: Record<string, string> = {
  overview: 'overview',
  'transactions-model': 'transactions-model',
  budget: 'planning',
  savings: 'planning',
  action: 'planning',
  reports: 'reports',
};

const DEFAULT_SUB: Record<string, string> = {
  overview: 'overview',
  'transactions-model': 'transactions-model',
  planning: 'budget',
  reports: 'reports',
};

export default function DashboardClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [supabase] = useState(() => createClient());

  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const urlTab = searchParams.get('tab');
  // Wizard step IDs become first-class deep links; 'training' alias for 'train'
  const wizardSteps = ['upload', 'categories', 'label', 'review', 'train'];
  const wizardStepAlias: Record<string, string> = { training: 'train' };
  const resolvedTab = urlTab ? (wizardStepAlias[urlTab] || urlTab) : urlTab;
  const isWizardStep = resolvedTab && wizardSteps.includes(resolvedTab);
  const activeTab = isWizardStep ? 'transactions-model' : (resolvedTab || 'overview');
  const activeSection = TAB_SECTION[activeTab];
  const section = SECTIONS.find((s) => s.id === activeSection)!;

  const goToTab = useCallback(
    (tab: string) => {
      router.replace(`/dashboard?tab=${tab}`, { scroll: false });
    },
    [router]
  );

  const goToSection = (sectionId: string) => goToTab(DEFAULT_SUB[sectionId]);

  useEffect(() => {
    // middleware.ts already gates unauthenticated visits server-side; this
    // is a backstop plus the user-email display.
    const checkAuth = async () => {
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) {
        router.push('/auth');
        return;
      }

      setUser(session.user);
      setLoading(false);
    };

    checkAuth();

    // If the session ends (signed out in another tab, refresh token revoked),
    // leave the dashboard instead of letting every request 401.
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event) => {
      if (event === 'SIGNED_OUT') {
        router.push('/auth');
      }
    });
    return () => subscription.unsubscribe();
  }, [supabase, router]);

  const handleLogout = async () => {
    await supabase.auth.signOut();
    router.push('/auth');
  };

  if (loading) return <DashboardLoading />;

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="sticky top-0 z-40 glass border-b border-edge/8">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
          <Link href="/dashboard" className="font-display text-lg font-bold tracking-tight">
            Financing<span className="text-accent-strong">.</span>
          </Link>
          <div className="flex items-center gap-2">
            <p className="mr-2 hidden text-sm text-muted sm:block">{user?.email}</p>
            <ThemeToggle />
            <Link
              href="/settings"
              aria-label="Settings"
              className="flex h-9 w-9 items-center justify-center rounded-pill border border-edge/10 text-muted transition-colors hover:text-ink hover:border-edge/25"
            >
              <Settings className="h-4 w-4" />
            </Link>
            <button
              onClick={handleLogout}
              aria-label="Sign out"
              className="flex h-9 w-9 items-center justify-center rounded-pill border border-edge/10 text-muted transition-colors hover:text-danger hover:border-danger/40"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Section tabs */}
        <div className="mx-auto max-w-7xl border-t border-edge/8 px-4 sm:px-6 lg:px-8">
          <TabBar
            tabs={SECTIONS}
            active={activeSection}
            onChange={goToSection}
            layoutId="section-tab"
          />
        </div>
      </header>

      {/* Content */}
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <OnboardingChecklist onNavigate={goToTab} activeTab={activeTab} />

        <TabPanel key={activeTab}>
          {activeTab === 'overview' && <StatsTab />}
          {activeTab === 'transactions-model' && (
            <TransactionsModelTab
              stepId={isWizardStep ? resolvedTab : undefined}
              onStepChange={(stepId) => goToTab(stepId)}
            />
          )}
          {activeTab === 'budget' && <BudgetTab />}
          {activeTab === 'savings' && <SavingsTab />}
          {activeTab === 'action' && <ActionTab onNavigate={goToTab} />}
          {activeTab === 'reports' && <ReportsTab />}
        </TabPanel>
      </main>
    </div>
  );
}
