'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  BrainCircuit,
  ChartPie,
  CheckCircle,
  FileSpreadsheet,
  FileText,
  LayoutDashboard,
  ListChecks,
  ListTodo,
  LogOut,
  PieChart,
  PiggyBank,
  Repeat,
  Search,
  Settings,
  SunMoon,
  Sparkles,
  Tags,
  Wallet,
  Workflow,
} from 'lucide-react';
import { createClient } from '@/utils/supabase';
import { TabBar, PillTabs, TabPanel, TabItem } from '@/components/ui/Tabs';
import CommandPalette, { Command } from '@/components/ui/CommandPalette';
import { toggleTheme } from '@/utils/theme';
import { SkeletonRows } from '@/components/ui/Skeleton';
import AccountMenu from '@/components/ui/AccountMenu';
import NotificationBell from '@/components/ui/NotificationBell';
import Tooltip from '@/components/ui/Tooltip';
import DashboardLoading from './loading';
import OnboardingTour from '@/components/onboarding/OnboardingTour';

// Each dashboard tab is code-split: only the active tab's JS (and its deps,
// e.g. StatsTab's recharts) loads, instead of shipping all of them upfront.
const tabLoading = () => <SkeletonRows rows={6} />;
const StatsTab = dynamic(() => import('@/components/tabs/StatsTab'), { loading: tabLoading, ssr: false });
const BudgetTab = dynamic(() => import('@/components/tabs/BudgetTab'), { loading: tabLoading, ssr: false });
const RuleTab = dynamic(() => import('@/components/tabs/RuleTab'), { loading: tabLoading, ssr: false });
const SavingsTab = dynamic(() => import('@/components/tabs/SavingsTab'), { loading: tabLoading, ssr: false });
const ActionTab = dynamic(() => import('@/components/tabs/ActionTab'), { loading: tabLoading, ssr: false });
const ReportsTab = dynamic(() => import('@/components/tabs/ReportsTab'), { loading: tabLoading, ssr: false });
const TransactionsModelTab = dynamic(() => import('@/components/tabs/TransactionsModelTab'), { loading: tabLoading, ssr: false });
const SubscriptionsTab = dynamic(() => import('@/components/tabs/SubscriptionsTab'), { loading: tabLoading, ssr: false });
const InsightsTab = dynamic(() => import('@/components/tabs/InsightsTab'), { loading: tabLoading, ssr: false });

/** Four sections with sub-tabs. Transactions & Model merged into one workflow. */
const SECTIONS: (TabItem & { subs: TabItem[] })[] = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard, subs: [] },
  {
    id: 'transactions-model',
    label: 'Transactions & Model',
    icon: Workflow,
    tourId: 'nav-transactions-model',
    subs: [],
  },
  {
    id: 'planning',
    label: 'Planning',
    icon: ChartPie,
    subs: [
      { id: 'budget', label: 'Budget', icon: Wallet },
      { id: 'rule-503020', label: '50/30/20', icon: PieChart },
      { id: 'savings', label: 'Savings', icon: PiggyBank },
      { id: 'subscriptions', label: 'Subscriptions', icon: Repeat },
      { id: 'insights', label: 'Insights', icon: Sparkles },
      { id: 'action', label: 'Action plan', icon: ListChecks },
    ],
  },
  { id: 'reports', label: 'Reports', icon: FileText, subs: [] },
];

/** Tab id → its section (for ActionTab's onNavigate and URL params). */
const TAB_SECTION: Record<string, string> = {
  overview: 'overview',
  'transactions-model': 'transactions-model',
  budget: 'planning',
  'rule-503020': 'planning',
  savings: 'planning',
  subscriptions: 'planning',
  insights: 'planning',
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
  const [bellOpen, setBellOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);

  const urlTab = searchParams.get('tab');
  // Wizard step IDs become first-class deep links; 'training' alias for 'train'
  const wizardSteps = ['upload', 'categories', 'label', 'review', 'train'];
  const wizardStepAlias: Record<string, string> = { training: 'train' };
  const resolvedTab = urlTab ? (wizardStepAlias[urlTab] || urlTab) : urlTab;
  const isWizardStep = resolvedTab && wizardSteps.includes(resolvedTab);
  const activeTab = isWizardStep ? 'transactions-model' : (resolvedTab || 'overview');
  const activeSection = TAB_SECTION[activeTab];

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

  // ⌘K entries: every section/sub-tab, every wizard step, and app actions.
  const commands: Command[] = useMemo(() => {
    const go = (tab: string) => () => goToTab(tab);
    const planning = SECTIONS.find((s) => s.id === 'planning')!.subs;
    return [
      { id: 'overview', label: 'Overview', group: 'Go to', icon: LayoutDashboard, keywords: 'home summary', run: go('overview') },
      { id: 'reports', label: 'Reports', group: 'Go to', icon: FileText, keywords: 'transactions table export search', run: go('reports') },
      ...planning.map((t) => ({
        id: t.id,
        label: t.label,
        group: 'Planning',
        icon: t.icon ?? ChartPie,
        keywords: 'planning',
        run: go(t.id),
      })),
      { id: 'upload', label: 'Upload statements', group: 'Transactions & Model', icon: FileSpreadsheet, keywords: 'import csv alipay wechat', run: go('upload') },
      { id: 'categories', label: 'Categories', group: 'Transactions & Model', icon: Tags, keywords: 'colors rename', run: go('categories') },
      { id: 'label', label: 'Label transactions', group: 'Transactions & Model', icon: ListTodo, keywords: 'tag merchants', run: go('label') },
      { id: 'review', label: 'Review suggestions', group: 'Transactions & Model', icon: CheckCircle, keywords: 'queue confirm', run: go('review') },
      { id: 'train', label: 'Train model', group: 'Transactions & Model', icon: BrainCircuit, keywords: 'retrain ml accuracy', run: go('train') },
      { id: 'settings', label: 'Settings', group: 'App', icon: Settings, keywords: 'income account password', run: () => router.push('/settings') },
      { id: 'theme', label: 'Toggle light / dark theme', group: 'App', icon: SunMoon, keywords: 'dark mode light mode', run: toggleTheme },
      { id: 'logout', label: 'Sign out', group: 'App', icon: LogOut, keywords: 'log out', run: handleLogout },
    ];
    // handleLogout is recreated each render but only closes over stable refs.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [goToTab, router]);

  if (loading) return <DashboardLoading />;

  const displayName: string = user?.user_metadata?.username || user?.email || '';
  const activeSectionData = SECTIONS.find((s) => s.id === activeSection);

  return (
    <div className="relative min-h-screen">

      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[60] focus:rounded-pill focus:bg-accent focus:px-4 focus:py-2 focus:text-accent-ink"
      >
        Skip to content
      </a>

      {/* Header: one row on desktop — wordmark, section nav, ⌘K, bell, account.
          Phones get a second row for the nav. */}
      <header className="sticky top-0 z-40 border-b border-edge/15 bg-bg">
        <div className="mx-auto flex w-full max-w-[1800px] items-center gap-6 px-4 sm:px-6 lg:px-8 2xl:px-12">
          <Link href="/dashboard" className="shrink-0 py-3 font-display text-xl font-semibold tracking-[-0.01em]">
            Financing<span className="text-accent">.</span>
          </Link>

          <div className="hidden md:block">
            <TabBar tabs={SECTIONS} active={activeSection} onChange={goToSection} layoutId="section-tab" />
          </div>

          <div className="ml-auto flex items-center gap-1">
            {/* ⌘K launcher — a quiet field on wide screens, an icon on phones */}
            <button
              onClick={() => setPaletteOpen(true)}
              className="mr-2 hidden h-9 w-56 items-center gap-2 rounded-md border border-edge/15 px-3 text-[13px] text-muted transition-colors hover:border-edge/30 hover:text-ink lg:flex xl:w-64"
              aria-label="Open command menu"
            >
              <Search className="h-3.5 w-3.5" aria-hidden="true" />
              <span className="flex-1 text-left">Jump to…</span>
              <span className="kbd">⌘K</span>
            </button>
            <Tooltip label="Search (⌘K)">
              <button
                onClick={() => setPaletteOpen(true)}
                aria-label="Open command menu"
                className="flex h-10 w-10 items-center justify-center rounded-md text-muted transition-colors hover:bg-edge/6 hover:text-ink lg:hidden"
              >
                <Search className="h-4 w-4" />
              </button>
            </Tooltip>
            <Tooltip label="Notifications" disabled={bellOpen}>
              <NotificationBell onOpenChange={setBellOpen} />
            </Tooltip>
            <AccountMenu name={displayName} onSignOut={handleLogout} />
          </div>
        </div>

        <div className="mx-auto w-full max-w-[1800px] border-t border-edge/10 px-4 sm:px-6 md:hidden">
          <TabBar tabs={SECTIONS} active={activeSection} onChange={goToSection} layoutId="section-tab-m" />
        </div>
      </header>

      {/* Content */}
      {/* Fluid shell: fills large screens (1920 included), caps only on ultrawides. */}
      <main id="main" className="mx-auto w-full max-w-[1800px] px-4 py-8 sm:px-6 sm:py-10 lg:px-8 2xl:px-12">
        <OnboardingTour
          onNavigate={goToTab}
          activeTab={isWizardStep ? resolvedTab! : activeTab}
        />

        {/* Planning sub-tabs (restored — dropped by accident in c08568f,
            which left Savings/Subscriptions/Insights/etc. unreachable). */}
        {activeSectionData && activeSectionData.subs.length > 0 && (
          <div className="mb-8">
            <PillTabs
              tabs={activeSectionData.subs}
              active={activeTab}
              onChange={goToTab}
              layoutId="planning-pill"
            />
          </div>
        )}

        <TabPanel key={activeTab}>
          {activeTab === 'overview' && <StatsTab onNavigate={goToTab} displayName={displayName} />}
          {activeTab === 'transactions-model' && (
            <TransactionsModelTab
              stepId={isWizardStep ? resolvedTab : undefined}
              onStepChange={(stepId) => goToTab(stepId)}
            />
          )}
          {activeTab === 'budget' && <BudgetTab />}
          {activeTab === 'rule-503020' && <RuleTab />}
          {activeTab === 'savings' && <SavingsTab />}
          {activeTab === 'subscriptions' && <SubscriptionsTab />}
          {activeTab === 'insights' && <InsightsTab />}
          {activeTab === 'action' && <ActionTab onNavigate={goToTab} />}
          {activeTab === 'reports' && <ReportsTab />}
        </TabPanel>
      </main>

      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} commands={commands} />
    </div>
  );
}
