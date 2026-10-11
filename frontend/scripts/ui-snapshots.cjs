/* UI snapshot harness — screenshots every page / dashboard tab in both themes
 * at desktop + phone width, against a production build with a mocked API.
 * See docs/DESIGN_SYSTEM.md §8.
 *
 * Usage (from frontend/):
 *   NEXT_PUBLIC_SUPABASE_URL=https://mockproj.supabase.co \
 *   NEXT_PUBLIC_SUPABASE_ANON_KEY=mock NEXT_PUBLIC_API_URL=http://localhost:9999 \
 *   npx next build && npx next start -p 3100 &
 *   node scripts/ui-snapshots.cjs <out-dir> [filter]
 *
 * `filter` limits shots by name substring (e.g. "overview" or "landing").
 * Playwright is resolved from the local install, else the global one.
 */
const path = require('path');
const fs = require('fs');
const { execSync } = require('child_process');

function loadPlaywright() {
  try {
    return require('playwright');
  } catch {
    const root = execSync('npm root -g').toString().trim();
    return require(path.join(root, 'playwright'));
  }
}

const BASE = process.env.UI_BASE || 'http://localhost:3100';
const OUT = process.argv[2] || 'ui-shots';
const FILTER = process.argv[3] || '';

// ── Mock data: realistic, translated merchants (UI is English-only) ─────────
const CATS = [
  ['c1', 'Food', 'amber'], ['c2', 'Transport', 'blue'], ['c3', 'Shopping', 'pink'],
  ['c4', 'Groceries', 'green'], ['c5', 'Housing', 'teal'], ['c6', 'Entertainment', 'rose'],
  ['c7', 'Travel', 'sky'], ['c8', 'Personal Care & Health', 'emerald'], ['c9', 'Education', 'olive'],
  ['c10', 'Transfers & Gifts', 'orange'], ['c11', 'Investments', 'cyan'], ['c12', 'Other', 'lime'],
];
const categories = CATS.map(([id, name, color]) => ({ id, name, color, is_catch_all: name === 'Other' }));
const MERCHANTS = [
  ['Luckin Coffee', 'Food', 18.5], ['Didi Chuxing', 'Transport', 32.4], ['Taobao', 'Shopping', 129],
  ['Meituan Delivery', 'Food', 46.8], ['Shanghai Metro', 'Transport', 4], ['Hema Fresh', 'Groceries', 212.6],
  ['JD.com', 'Shopping', 349], ['Ctrip', 'Travel', 1280], ['Bilibili', 'Entertainment', 25],
  ['Watsons', 'Personal Care & Health', 88.9], ['FamilyMart', 'Food', 23.5], ['Pinduoduo', 'Shopping', 57.3],
];
// v5 home currency used throughout the mocks: USD at an ECB-like CNY rate.
const USD_RATE = 0.1387;
const RATE_DATE = '2026-09-30';
const home = (cny) => +(cny * USD_RATE).toFixed(2);
const tx = (i) => {
  const [merchant, category, amount] = MERCHANTS[i % MERCHANTS.length];
  const day = String(28 - (i % 27)).padStart(2, '0');
  return {
    id: `t${i}`, date: `2026-09-${day}`, timestamp: `2026-09-${day}T12:30:00Z`, merchant,
    description: `${merchant} order`, amount: +(amount * (1 + (i % 5) / 10)).toFixed(2),
    category, category_id: (CATS.find((c) => c[1] === category) || CATS[11])[0],
    confidence: 0.42 + ((i * 7) % 50) / 100, suggested_category: category,
    is_split: false, splits: null, label_source: i % 3 ? 'model' : 'override',
    bucket: ['Food', 'Transport', 'Groceries', 'Housing'].includes(category) ? 'Need' : 'Want',
    // v5 (docs/contracts/API_V5.md): kind / flow subtype / source / home amount.
    kind: 'expense', flow_subtype: null, source: i % 2 ? 'wechat' : 'alipay',
    amount_home: +(amount * (1 + (i % 5) / 10) * USD_RATE).toFixed(2),
  };
};
// v5 non-expense rows (Reports with kind=income|transfer|all).
const flowTx = [
  { merchant: 'Acme Shanghai Ltd. (payroll)', amount: 18000, kind: 'income', flow_subtype: 'salary', source: 'bank', day: '10' },
  { merchant: 'Yu\'e Bao interest', amount: 12.84, kind: 'income', flow_subtype: 'interest', source: 'alipay', day: '01' },
  { merchant: 'Li Wei', amount: 260, kind: 'transfer', flow_subtype: 'aa_collection', source: 'wechat', day: '21' },
  { merchant: 'Zhang Min', amount: -88.8, kind: 'transfer', flow_subtype: 'red_packet', source: 'wechat', day: '18' },
  { merchant: 'China Merchants Bank (top-up)', amount: 2000, kind: 'transfer', flow_subtype: 'top_up', source: 'alipay', day: '05' },
  { merchant: 'Landlord (Mr. Chen)', amount: 4500, kind: 'transfer', flow_subtype: 'p2p_transfer', source: 'wechat', day: '02' },
].map((r, i) => ({
  id: `f${i}`, date: `2026-09-${r.day}T09:00:00`, merchant: r.merchant, description: r.merchant,
  amount: r.amount, category: r.kind === 'income' ? 'Income' : 'Transfer', category_id: null,
  is_split: false, splits: null, label_source: 'none', bucket: null,
  kind: r.kind, flow_subtype: r.flow_subtype, source: r.source, amount_home: +(r.amount * USD_RATE).toFixed(2),
}));
const months = ['2025-10', '2025-11', '2025-12', '2026-01', '2026-02', '2026-03', '2026-04', '2026-05', '2026-06', '2026-07', '2026-08', '2026-09'];
const spend = [9840, 11210, 14380, 12950, 8710, 10420, 11890, 10120, 13560, 12230, 13610, 12480];
const income = [18000, 18000, 21500, 18000, 18000, 18000, 18012.5, 18000, 18000, 18000, 18000, 18012.84];
const transfersIn = [120, 0, 860, 300, 0, 45, 200, 0, 520, 80, 0, 260];
const transfersOut = [4500, 4500, 4688, 4500, 6200, 4500, 4500, 4588.8, 4500, 4500, 4500, 4588.8];

const MOCKS = {
  '/dashboard/summary': { total_transactions: 1284, labeled_transactions: 1093, labeling_percentage: 85.1, total_spend: 141400.5, monthly_income: 18000,
    month: '2026-09', month_spend: 12480, month_income: 18012.84, month_income_source: 'statements',
    home: { currency: 'USD', total_spend_home: 19694.62, month_spend_home: home(12480), month_income_home: home(18012.84), rate_asof: RATE_DATE, rate: USD_RATE } },
  '/dashboard/cashflow': { currency_home: 'USD', own_account_moved: 26400, months: months.map((month, i) => ({
    month, spend: spend[i], income: income[i], transfers_in: transfersIn[i], transfers_out: transfersOut[i],
    net: +(income[i] - spend[i]).toFixed(2), spend_home: home(spend[i]), income_home: home(income[i]), net_home: home(income[i] - spend[i]) })) },
  '/fx/currencies': { base: 'CNY', source: 'European Central Bank via Frankfurter', supported: [
    ['USD', 'US Dollar'], ['EUR', 'Euro'], ['GBP', 'British Pound'], ['AUD', 'Australian Dollar'], ['CAD', 'Canadian Dollar'],
    ['JPY', 'Japanese Yen'], ['KRW', 'South Korean Won'], ['SGD', 'Singapore Dollar'], ['HKD', 'Hong Kong Dollar'], ['CHF', 'Swiss Franc'],
    ['NZD', 'New Zealand Dollar'], ['SEK', 'Swedish Krona'], ['NOK', 'Norwegian Krone'], ['DKK', 'Danish Krone'], ['PLN', 'Polish Zloty'],
    ['CZK', 'Czech Koruna'], ['HUF', 'Hungarian Forint'], ['INR', 'Indian Rupee'], ['IDR', 'Indonesian Rupiah'], ['MYR', 'Malaysian Ringgit'],
    ['PHP', 'Philippine Peso'], ['THB', 'Thai Baht'], ['ZAR', 'South African Rand'], ['BRL', 'Brazilian Real'], ['MXN', 'Mexican Peso'],
    ['ILS', 'Israeli New Shekel'], ['TRY', 'Turkish Lira'], ['ISK', 'Icelandic Krona'], ['RON', 'Romanian Leu'],
  ].map(([code, name]) => ({ code, name })) },
  '/dashboard/by-category': { categories: [
    { category: 'Food', total_amount: 4210.4, transaction_count: 212 }, { category: 'Transport', total_amount: 1980.2, transaction_count: 98 },
    { category: 'Shopping', total_amount: 1620.7, transaction_count: 41 }, { category: 'Housing', total_amount: 2600, transaction_count: 1 },
    { category: 'Groceries', total_amount: 980.3, transaction_count: 22 }, { category: 'Entertainment', total_amount: 412.5, transaction_count: 9 },
    { category: 'Personal Care & Health', total_amount: 676.1, transaction_count: 7 } ] },
  '/dashboard/trends': { currency_home: 'USD', trends: months.map((date, i) => ({ date, total_spend: spend[i], total_spend_home: home(spend[i]) })) },
  '/dashboard/notifications': { unread_count: 2, notifications: [
    { id: 'n1', type: 'budget_alert', payload: { category: 'Food', current: 4210, limit: 4000, overage: 210, pct: 105 }, read_at: null, created_at: '2026-09-28T09:00:00Z' },
    { id: 'n2', type: 'training_complete', payload: { cv_accuracy: 0.874 }, read_at: null, created_at: '2026-09-27T21:00:00Z' } ] },
  '/dashboard/tour': { finished: true, step: null },
  '/categories': { categories },
  '/dashboard/review-queue': { transactions: Array.from({ length: 8 }, (_, i) => tx(i)), count: 23, type: 'low_confidence' },
  '/dashboard/rule-503020': { month: '2026-09', available_months: ['2026-09', '2026-08', '2026-07'], income: 18000, buckets: {
    needs: { target_pct: 50, target_amount: 9000, spent: 7980, categories: [{ category: 'Housing', amount: 2600 }, { category: 'Food', amount: 4210 }, { category: 'Transport', amount: 1170 }] },
    wants: { target_pct: 30, target_amount: 5400, spent: 3720, categories: [{ category: 'Shopping', amount: 1620 }, { category: 'Entertainment', amount: 412 }, { category: 'Travel', amount: 1688 }] },
    savings: { target_pct: 20, target_amount: 3600, spent: 6300, categories: [] } } },
  '/dashboard/action': { actions: [
    { type: 'over_budget', category: 'Food', current: 4210, limit: 4000, overage: 210, pct: 105 },
    { type: 'approaching_budget', category: 'Shopping', current: 1620, limit: 1800, pct: 90 },
    { type: 'pending_review', count: 23, message: '23 transactions are waiting for your review.' } ] },
  '/dashboard/insights': { category_trends: [
    { category: 'Food', current: 4210, avg_3mo: 3620, pct_change: 16.3 }, { category: 'Transport', current: 1980, avg_3mo: 2240, pct_change: -11.6 },
    { category: 'Shopping', current: 1620, avg_3mo: 1490, pct_change: 8.7 } ],
    flagged_transactions: [{ id: 'f1', merchant: 'Ctrip', category: 'Travel', amount: 3280, timestamp: '2026-09-14T08:00:00Z' }] },
  '/subscriptions': { monthly_total: 143, subscriptions: [
    { id: 's1', merchant: 'iCloud+', cadence: 'monthly', typical_amount: 21, last_seen: '2026-09-03', is_confirmed: true, categories: { name: 'Other' } },
    { id: 's2', merchant: 'Bilibili Premium', cadence: 'monthly', typical_amount: 25, last_seen: '2026-09-11', is_confirmed: true, categories: { name: 'Entertainment' } },
    { id: 's3', merchant: 'NetEase Cloud Music', cadence: 'monthly', typical_amount: 15, last_seen: '2026-09-19', is_confirmed: false, categories: { name: 'Entertainment' } },
    { id: 's4', merchant: 'Keep Fitness', cadence: 'monthly', typical_amount: 82, last_seen: '2026-09-21', is_confirmed: false, categories: { name: 'Personal Care & Health' } } ] },
  '/dashboard/reports': { transactions: Array.from({ length: 20 }, (_, i) => tx(i)), total_count: 1284, page: 1, per_page: 20, kind: 'expense', currency_home: 'USD' },
  '/training': { training_runs: [
    { id: 'r2', status: 'succeeded', cv_accuracy: 0.874, f1_macro: 0.81, n_labeled_samples: 1093, created_at: '2026-09-27T20:55:00Z', finished_at: '2026-09-27T21:00:00Z' },
    { id: 'r1', status: 'succeeded', cv_accuracy: 0.836, f1_macro: 0.77, n_labeled_samples: 640, created_at: '2026-08-30T10:00:00Z', finished_at: '2026-08-30T10:04:00Z' } ] },
  '/dashboard/budget': (() => {
    const rows = [
      { category: 'Food', monthly_budget: 4000, current_spend: 4210, type: 'Need' }, { category: 'Transport', monthly_budget: 2400, current_spend: 1980, type: 'Need' },
      { category: 'Shopping', monthly_budget: 1800, current_spend: 1620, type: 'Want' }, { category: 'Housing', monthly_budget: 2600, current_spend: 2600, type: 'Need' },
      { category: 'Entertainment', monthly_budget: 800, current_spend: 412, type: 'Want' },
    ].map((r) => ({ ...r, monthly_budget_home: home(r.monthly_budget), current_spend_home: home(r.current_spend) }));
    const total_budget = rows.reduce((s, r) => s + r.monthly_budget, 0);
    const total_spent = rows.reduce((s, r) => s + r.current_spend, 0);
    return { budget_config: { monthly_income: 18000, currency: 'CNY' }, month: '2026-09', available_months: ['2026-09', '2026-08', '2026-07'], category_budgets: rows,
      total_budget, total_spent, currency_home: 'USD', total_budget_home: home(total_budget), total_spent_home: home(total_spent) };
  })(),
  '/uploads': { uploads: [
    { id: 'u3', original_filename: 'cmb_statement_202609.csv', file_type: 'bank', created_at: '2026-09-29T08:00:00Z', row_count: 41, status: 'parsed', parser_version: 2 },
    { id: 'u1', original_filename: 'alipay_record_202609.csv', file_type: 'alipay', created_at: '2026-09-28T10:00:00Z', row_count: 214, status: 'parsed', parser_version: 2 },
    { id: 'u2', original_filename: 'wechat_bill_202609.xlsx', file_type: 'wechat', created_at: '2026-09-28T10:01:00Z', row_count: 97, status: 'parsed', parser_version: 1 } ] },
  '/dashboard/savings': { savings_goal_monthly: 4000, income: 18000, current_spend: 12480, projected_savings: 5520, average_monthly_spend: 11780, is_anomaly: false },
  '/settings/profile': { profile: { id: 'u', username: 'chinsanaa', email_verified_at: '2026-07-01T00:00:00Z', onboarding_phase: 'done', created_at: '2026-07-01T00:00:00Z',
    alert_email_enabled: true, alert_threshold_pct: 90, budget_inapp_enabled: true, pending_review_inapp_enabled: true, monthly_overview_email_enabled: false, monthly_income: 18000, home_currency: 'USD' } },
};

function mockFor(url) {
  const u = new URL(url);
  const p = u.pathname.replace(/\/$/, '');
  // v5: Reports honors ?kind= (default expense) so cash-flow views have rows.
  if (p === '/dashboard/reports') {
    const kind = u.searchParams.get('kind') || 'expense';
    const exp = Array.from({ length: 20 }, (_, i) => tx(i));
    const rows = kind === 'expense' ? exp : kind === 'all' ? [...flowTx, ...exp] : flowTx.filter((r) => r.kind === kind);
    return { ...MOCKS['/dashboard/reports'], kind, transactions: rows, total_count: kind === 'expense' ? 1284 : rows.length };
  }
  const keys = Object.keys(MOCKS).sort((a, b) => b.length - a.length);
  const k = keys.find((key) => p === key || p.startsWith(key + '/') || p.startsWith(key));
  return k ? MOCKS[k] : {};
}

const session = {
  access_token: 'mock', token_type: 'bearer', expires_in: 3600 * 24 * 365,
  expires_at: Math.floor(Date.now() / 1000) + 3600 * 24 * 365, refresh_token: 'mock',
  user: { id: 'u', aud: 'authenticated', email: 'chinsanaa@example.com', user_metadata: { username: 'chinsanaa' } },
};

const PUBLIC = [['landing', '/'], ['auth', '/auth'], ['signup', '/auth?mode=signup'], ['privacy', '/privacy'], ['guide', '/guide'], ['404', '/nope']];
const TABS = ['overview', 'upload', 'categories', 'label', 'review', 'train', 'budget', 'rule-503020', 'savings', 'subscriptions', 'insights', 'action', 'reports'];
const PRIVATE = [...TABS.map((t) => [t, `/dashboard?tab=${t}`]), ['settings', '/settings']];

(async () => {
  const { chromium } = loadPlaywright();
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const errors = [];
  for (const theme of ['light', 'dark']) {
    for (const [w, h, size] of [[1440, 900, 'desktop'], [390, 844, 'phone']]) {
      for (const authed of [false, true]) {
        const ctx = await browser.newContext({ viewport: { width: w, height: h }, colorScheme: theme });
        await ctx.addInitScript((t) => { try { localStorage.setItem('theme', t); } catch {} }, theme);
        if (authed) {
          await ctx.addCookies([{ name: 'sb-mockproj-auth-token', value: encodeURIComponent(JSON.stringify(session)), url: BASE }]);
        }
        await ctx.route(/localhost:9999|mockproj\.supabase\.co/, (route) =>
          route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockFor(route.request().url())) })
        );
        const page = await ctx.newPage();
        page.on('pageerror', (e) => errors.push(`${page.url()}: ${e.message}`));
        for (const [name, url] of authed ? PRIVATE : PUBLIC) {
          const shot = `${name}-${theme}-${size}`;
          if (FILTER && !shot.includes(FILTER)) continue;
          await page.goto(BASE + url, { waitUntil: 'networkidle' });
          await page.waitForTimeout(600);
          for (let y = 0; y < 8000; y += 500) { await page.mouse.wheel(0, 500); await page.waitForTimeout(80); }
          await page.waitForTimeout(900);
          await page.screenshot({ path: path.join(OUT, `${shot}.png`), fullPage: true });
        }
        await ctx.close();
      }
    }
  }
  await browser.close();
  console.log(`shots → ${OUT}`);
  if (errors.length) { console.log('PAGE ERRORS:\n' + errors.join('\n')); process.exitCode = 1; }
})();
