# Competitor Audit — October 2026

**Date:** 2026-10-11 · **Audit:** A1 "Competitor auditor" · **Product:** Financing (web)

---

## 1. Scope, method, sources policy

**Scope.** We compared Financing with 13 personal-finance products and 4 China bill-import tools. The questions were: what does each one do for a foreigner whose money moves through Alipay and WeChat Pay, how does it present itself, and where are we weaker today?

**Method.**
1. We fetched each product's public homepage or pricing page on 2026-10-11 and summarized only what the page says.
2. Where the page said nothing, we used web-search snippets or third-party reviews. These are labeled **[snippet]** or **[3rd-party]**.
3. Claims carried over from the earlier research pass that we could not re-check today are labeled **[unverified]**.
4. We read Financing's own code and cite it as `path:line`.

**Sources policy.**
- Every external claim has a URL. All URLs were accessed **2026-10-11**.
- Vendor homepages are marketing and are reported as "the vendor says".
- **Lunch Money's site (lunchmoney.app) returned HTTP 403 to our fetcher.** Everything about Lunch Money comes from search snippets of its own help and compare pages.
- No numbers are invented. A "—" means the source did not say.
- Chinese names are shown with romanization and an English gloss.

---

## 2. Competitor profiles

**Copilot Money** ([copilot.money](https://www.copilot.money/))
- **Target user:** US users who want spending, budgets, investments and net worth in one place.
- **Data in:** bank and brokerage connections. Real-estate value comes from a Zillow URL.
- **Categorization:** the vendor says AI "learns your spending patterns and tags every transaction automatically".
- **Platforms:** web, iPhone, iPad, Mac. Android is not mentioned.
- **Price:** $7.92/month, billed $95/year. 1-month trial. "No ads, no hidden fees".
- **Landing:** short emotional hero ("Your money, beautifully organized."), a **"Test drive for free"** demo before you connect anything, and a "Why isn't Copilot free?" link. Social proof is layered: Apple awards, a creator endorsement, then user posts. The footer has four columns, including a "Privacy & Security" page.

**Monarch** ([monarch.com](https://www.monarch.com/), [pricing](https://www.monarch.com/pricing))
- **Target user:** households in the US and Canada. Partners share one view.
- **Data in:** sync through multiple data providers. The vendor claims "13,000+ financial institutions".
- **Features:** automatic categorization, recurring-bill and subscription detection, goals.
- **Platforms:** web, iOS, Android.
- **Price:** Core is $14.99/month or $99.99/year, with a 7-day trial.
- **Landing:** hero "The modern way to manage money.", "No ads", and stacked press quotes (WSJ, Forbes, etc.). The footer is large: comparison pages against YNAB, Mint and others, calculators, a bank-connection status page and a system-health page.

**Empower Personal Dashboard** ([empower.com/tools](https://www.empower.com/tools))
- **What it is:** free budgeting, cash-flow, net-worth and retirement tools, used through account aggregation.
- **How it makes money:** the tools feed Empower's fee-based advisory services, which start above $250,000 invested.
- **Disclosure:** the page says the site is paid "up to $250 for each individual lead" and calls this "a material conflict of interest".
- **Lesson for us:** "free" is paid for by advice sales. This is the opposite of the "how we make money" honesty we want to show.

**YNAB** ([ynab.com](https://www.ynab.com/))
- **Method:** envelope ("give every dollar a job") budgeting, taught as a skill.
- **Data in:** bank sync through Plaid (footer disclaimer). The homepage does not mention file import.
- **Platforms:** iOS, Android, web.
- **Price:** $14.99/month or $109/year, from the page's structured data. The trial is 34 days with no card required.
- **Landing:** a three-step "how it works" section, then the heaviest social proof in the set: survey percentages, Trustpilot and app-store ratings, press and awards, and testimonials. The footer covers legal, accessibility and the API.

**The Budgeting App** ([thebudgeting.app](https://thebudgeting.app/))
- **Data in:** fast manual entry. Bank sync is only in the paid Pro Sync tier, and only in Australia, the US and Canada.
- **Price:** free with no ads. Pro tier prices are not listed.
- **Privacy:** offline-first, "no sign-up required" to start.
- **Landing:** the best **live demo** in the set. An animated bill split ($75 into two $37.50 shares) is followed by budgets, a period summary and charts, with a "Replay" button. A "A tool that respects you" section explains its values. The footer has guides and comparison pages.

**Expensify** ([expensify.com](https://www.expensify.com/))
- **Target user:** mainly business expense reporting. Personal tracking is free.
- **Data in:** receipt capture (photo, email, text) and card feeds.
- **Currency:** reimbursement "in their local currency anywhere". The page does not explain how conversion works.
- **Price:** company plans from $5 per member.
- **Fit for us:** not a budgeting competitor, but it shows how receipt capture and currency handling are pitched.

**Lunch Money** (lunchmoney.app, **403 to our fetcher**; [multicurrency help](https://support.lunchmoney.app/settings/multicurrency) **[snippet]**, [Monarch-alternative page](https://lunchmoney.app/compare/monarch-alternative) **[snippet]**, [College Investor review](https://thecollegeinvestor.com/45433/lunch-money-review/) **[3rd-party]**)
- **Positioning:** the multi-currency budgeting app. It claims "160+" currencies, and one primary currency is used for all totals.
- **Data in:** CSV import from any source plus a public API. Plaid covers supported banks.
- **Price:** sources conflict, from $60/year up to $10/month or $100/year. Treat as **unverified**.
- **Gap:** we did not confirm whether conversion uses the rate on each transaction's date.

**Actual Budget** ([actualbudget.org](https://actualbudget.org/))
- **What it is:** open-source, local-first envelope budgeting.
- **Data in:** QIF, OFX, QFX, CAMT.053 and CSV import, plus YNAB importers. Bank sync uses GoCardless (EU and UK) and SimpleFIN (US and Canada).
- **Price:** self-hosting is free. PikaPods offers paid hosting.
- **Landing:** a **public demo** at demo.actualbudget.org. The homepage does not mention multi-currency.

**Wallet by BudgetBakers** ([budgetbakers.com](https://budgetbakers.com/))
- **Data in:** bank sync. The vendor claims "15,000+" bank connections.
- **Platforms and languages:** iOS, Android and web, in 50 languages.
- **Categorization:** described as one that "learns over time".
- **Price:** free trial. Prices are not on the homepage.
- **Multi-currency:** not mentioned on the homepage.

**Spendee** ([spendee.com](https://www.spendee.com/))
- **Data in:** bank, e-wallet and crypto-wallet connections, plus manual cash entries.
- **Other features:** multi-currency (pitched to travelers and digital nomads), shared wallets, budgets with alerts, savings goals.
- **Price:** Premium and Plus tiers. Prices are not on the homepage.

**Wise Insights** ([Wise blog, Android insights](https://wise.com/gb/blog/cheap-easy-and-insightful-android-say-hello-to-insights) **[snippet; 2020 source]**)
- **What it is:** the money-transfer account automatically sorts its own card spending into 15 categories, and users can re-categorize.
- **Limit:** it only covers money spent through Wise, so it cannot see Alipay or WeChat.
- **Currency:** it does show spending by currency.

**钱迹 Qianji ("Money Trail")** ([qianjiapp.com](https://www.qianjiapp.com/))
- **What it is:** a Chinese bookkeeping app: "无广告、无开屏、无理财" ("no ads, no splash screen, no financial products").
- **Platforms:** 9 surfaces, including HarmonyOS, Windows and macOS.
- **Vendor claims:** 30M+ downloads.
- **Data in:** a "unique import feature" for other platforms' bills. The homepage does not name Alipay or WeChat; that detail is **[unverified]**.
- **Language:** the UI is Chinese.

**随手记 Suishouji ("Jot-It-Down Bookkeeping")** ([sui.com](https://www.sui.com/))
- **What the homepage shows:** only a tagline ("多赚会花每一天" ≈ "earn more, spend wisely, every day").
- **Unverified (earlier research):** Alipay and WeChat bill import, Chinese-only UI, a paid membership.

**Alipay/WeChat bill-import apps**

| App | What we found | Source |
|---|---|---|
| 今日记账 Jinri Jizhang ("Today's Bookkeeping") | The App Store listing says it imports WeChat and Alipay bills and auto-categorizes them. It also says it excludes transfers, detects refunds and de-duplicates, and that imported totals match what WeChat and Alipay show. Membership is ¥5/month. | [App Store](https://apps.apple.com/hk/app/id1527956057) **[snippet]** |
| 月儿记账 Yue'er Jizhang ("Moon Bookkeeping") | The App Store listing says it imports WeChat and Alipay bills and auto-categorizes by income/expense type. It also imports Suishouji and Shark Bookkeeping (鲨鱼记账) data. Advanced features are paid. | [App Store](https://apps.apple.com/bg/app/id1594162847) **[snippet]** |
| 账单精灵 Zhangdan Jingling ("Bill Sprite") | Our search returned nothing. | **[unverified]** |

All three are Chinese-language only.

**deb-sig/double-entry-generator** ([GitHub](https://github.com/deb-sig/double-entry-generator))
- **What it is:** an Apache-2.0 command-line tool that converts Alipay, WeChat, several Chinese banks, HSBC HK, Meituan, JD and others into Beancount or Ledger files.
- **Categorization:** YAML rules matched on counterparty, category or time.
- **Fit for us:** the strongest technical proof that these exports can be parsed reliably. It is for engineers only: no UI, rules not learning, no translation.

**Key finding.** We found no product, Western or Chinese, that combines **Alipay/WeChat statement import with an English UI and translated merchants**.
- **Western apps** (Copilot, Monarch, YNAB, Wallet, Spendee): their data-in is bank sync through aggregators (Plaid, GoCardless, SimpleFIN) that cover US, EU and UK banks. None documents a way to read Alipay or WeChat exports. Generic CSV importers (Actual, Lunch Money) would need manual column mapping of Chinese headers and still show Chinese merchant names.
- **Chinese apps** (Qianji, Suishouji, Jinri Jizhang, Yue'er Jizhang): they read these exports, but the UI is Chinese-only.

That gap is our position.

---

## 3. Feature comparison matrix

Legend: ✓ yes · ✗ no · ~ partial · — not stated by source · ? unverified

| Feature | **Financing (today)** | Copilot | Monarch | YNAB | Lunch Money | Actual | Wallet / Spendee | Qianji / bill-import apps |
|---|---|---|---|---|---|---|---|---|
| Data import | Upload of Alipay CSV and WeChat XLSX/CSV (`backend/routes/uploads.py:346-369`) | Bank sync | Bank sync | Bank sync (Plaid) | Plaid + CSV + API [snippet] | Files (OFX/QIF/CSV…) + sync | Bank sync | File import |
| Alipay/WeChat import | ✓ | ✗ | ✗ | ✗ | ✗ (generic CSV only) | ✗ (generic CSV only) | ✗ | ✓ (Jinri, Yue'er [snippet]; Qianji ?) |
| English UI | ✓ (`PRODUCT.md:38`) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ (Wallet 50 languages) | ✗ |
| Merchant translation | ✓ (`Landing.tsx:16`) | n/a | n/a | n/a | n/a | n/a | n/a | ✗ |
| Auto-categorization | Per-user classifier trained on your own labels; low-confidence guesses go to review (`Landing.tsx:17-18`) | AI, learns | Auto | Rules / manual | Rules [snippet] | Rules | "Learns" (Wallet) | Rules / type mapping |
| Budgeting method | Category budgets + 50/30/20 + savings goal | Budgets | Budgets + flex | Envelope | Budgets | Envelope | Budgets | Budgets |
| Goals | ~ one monthly savings goal | — | ✓ | ✓ (targets) | — | ~ | ✓ (Spendee) | ? |
| Subscription detection | ✓ | — | ✓ | — | — | — | — | ? |
| Multi-currency (by transaction date?) | ✗ CNY only (`format.ts:14`) | — | — | — | ✓ 160+, one primary currency; date basis ? | — | ✓ Spendee; date basis — | ✗ |
| Income / transfers | Income dropped (`parse.py:80`); own-account repayments excluded (`parse.py:36`); P2P transfers kept as spend | — | ✓ cash flow | ✓ | — | ✓ | — | Jinri: transfers excluded [snippet] |
| Export guides | ✗ | n/a | Bank-status page | n/a | — | Docs | — | In-app ? |
| Reports / export | Reports tab | ✓ | ✓ | ✓ | ✓ API | ✓ | ✓ | ✓ |
| Mobile | Responsive web only | iOS/Mac | iOS/Android | iOS/Android | Web [snippet] | Web/desktop | iOS/Android | iOS/Android |
| Privacy stance | "Private per account" (`Landing.tsx:20`); no business-model statement | "Why isn't it free?" link | "No ads" | Plaid disclaimer | — | Local-first, OSS | — | "No ads" (Qianji) |
| Price | Free (no pricing page) | $95/yr | $99.99/yr | $109/yr | ? | Free / hosting | — | Jinri ¥5/mo [snippet] |

---

## 4. Landing-page teardown

### What the best landing pages share

| Pattern | Best example | What it does |
|---|---|---|
| Short emotional hero next to real UI | Copilot ("Your money, beautifully organized.") | Five words, then the actual app |
| Live or try-it demo | The Budgeting App (animated bill split + Replay); Actual (public demo app); Copilot ("Test drive for free") | Lets you see the product before signing up |
| Layered, honest social proof | YNAB (survey + ratings + press + testimonials); Monarch (press quotes) | Several kinds of evidence, each with a source |
| "How we make money" / privacy section | Copilot ("Why isn't Copilot free?"); The Budgeting App ("A tool that respects you"); Empower (lead-fee disclosure, honest but unflattering) | Answers "what's the catch?" |
| Low-commitment first step | YNAB (34 days, no card); The Budgeting App (no sign-up); Actual (demo) | The first click costs nothing |
| One repeated CTA | Monarch ("Try Monarch free for 7 days") | The same verb everywhere |
| Trust-building footer | Monarch (status, comparisons, calculators); YNAB (security, accessibility, API) | The footer works as a second navigation and a trust signal |

### How ours compares today

Sources: `frontend/src/components/landing/Landing.tsx`, `StatementSheet.tsx`.

**What works:**
- **Hero:** "Every yuan, accounted for." (`Landing.tsx:79`) is short and good.
- **CTA:** "Start free" repeats (`:65`, `:88`). The close switches to "Create your account" (`:136`), a slight inconsistency.
- **Demo element:** a synthetic statement of seven rows, with stamps and "Stamp again" (`StatementSheet.tsx:14-22, 41`). This is a demo of the *mechanism*, not of the product.

**What is missing:**
- **No real product UI.** No dashboard, charts, budget or label card appear. Visitors can't try the product with a sample file. Below the hero, the page is text only: a `dl` of six rows (`Landing.tsx:14-21, 117-124`).
- **No format logos.** "Alipay" and "WeChat Pay" appear only as words. The single biggest differentiator is not shown visually.
- **No "how we make money / privacy" story.** There is one line, "Private per account" (`:20`). Nothing says who pays for the servers.
- **Thin footer.** One line plus Privacy and Terms (`:147-160`). No export guide, no contact, no GitHub or status link, no "built for expats in China" statement.
- **No social proof.** This is correct: `PRODUCT.md:53-56` forbids fabricated proof. We should replace it with *verifiable* proof: the real parser, the formats we support, and an open method.

**Verdict:** honest but **"boring"**. Mostly text, with no product demo and no visual cue that this is *the* Alipay/WeChat tool in English.

---

## 5. Our weak points

| ID | Title | Severity | Evidence | Owner | Acceptance check |
|---|---|---|---|---|---|
| **W-01** | Landing has no live product demo or format logos | High | `Landing.tsx:99-101` shows only the synthetic `StatementSheet`; the rest is a text `dl` (`:117-124`); no Alipay or WeChat logo anywhere on the landing | D1 (+D0 logos) | The landing shows real product UI (an interactive "Sorted" demo using sample data) above the fold. Small official Alipay and WeChat Pay logos sit next to the upload claim. Works at 375px. Solid colors only. |
| **W-02** | Thin, bland footer | Med | `Landing.tsx:147-160`: one tagline line + Privacy + Terms | D2 | The footer has grouped links (product, export guide, privacy and how we make money, legal, contact) and a one-line expat positioning statement. No fabricated proof. |
| **W-03** | Display serif feels formal and intimidating | Med | `layout.tsx:3,11` uses Newsreader for `--font-display`; it is used for every headline and figure (`DESIGN_SYSTEM.md:91`) | D0 | `font-display` is Fraunces with `SOFT 100`, `WONK 0`. Headline and `.num` figures render in Fraunces. Tabular figures still line up in tables. |
| **W-04** | Warm cream paper | Med | `globals.css:16` `--bg: 244 241 234`; `layout.tsx:16` theme color `#f4f1ea` | D0 | `--bg`, `--surface`, `--surface-2` and the theme color move to the approved grey-green ledger paper. `muted` stays at ≥4.5:1. Light and dark both pass. |
| **W-05** | Category palette not tuned to the paper | Med | `categoryColors.ts:10-16, 25-38` and `globals.css:34-45` were validated against warm paper, not the new background | D0 | All 12 keys are retuned for the new paper. The validator passes 3:1 contrast, CVD and ΔE in both themes. **No purple. Keys unchanged, so no DB migration.** |
| **W-06** | Income rows dropped; no cash flow | High | `parse.py:80` `keep = is_expense \| is_refund`; `:242`, `:280` keep only `收/支 == 支出` ("expense") | B1 + B2 + D4 | The parser keeps income, red packets (红包) received, AA (split-bill) repayments and own-account transfers, each with a type. A cash-flow view shows in, out and net per month. Totals reconcile with a sample statement. |
| **W-07** | CNY only; no home-currency view | High | `format.ts:10-14` hardcodes `¥`; `settings.py:29` accepts `currency`, which `dashboard.py:279` returns, but no UI uses it; `PRODUCT.md:39` | B3 + C0 + D4 + D5 | The user picks a home currency. Amounts convert at the rate **on each transaction's date**, with the rate source cited. CNY stays primary, and the home-currency figure appears beside it. |
| **W-08** | Generic bank CSV parser unused | Med | `parse.py:111` `parse_generic_bank_csv` is called only by the CLI loader (`parse.py:430`); `uploads.py:346-369` `detect_source` returns only `alipay`/`wechat`, else `None`; enum `transaction_source` = alipay, wechat, manual (`supabase/migrations/20260703000000_initial_schema.sql:6`, `…20260814050000…:2`) | B2 + D3 | Uploading a bank CSV (e.g. China Merchants Bank or ICBC export) is detected, mapped (with a column-confirm step) and stored with its own source value. |
| **W-09** | No statement export guide | High | No guide route in `frontend/src/app/` (only auth, dashboard, privacy, settings, terms); upload claims assume users know how to export | D3 | A step-by-step English guide (with screenshots) for Alipay, WeChat and a bank CSV, linked from Upload, the landing and the footer. Chinese UI labels are given with English translations. |
| **W-10** | Parser counting bugs | High | (a) **Partial refunds:** `parse.py:84` negates the whole row amount for any `退款` ("refund") status; the refunded sub-amount is never read. (b) **WeChat `朋友已收钱` ("friend has received the money"):** `parse.py:277` treats only `支付成功` ("payment succeeded") and `已转账` ("transferred") as settled, so these P2P rows are dropped. (c) **Alipay `交易关闭` ("transaction closed"):** `parse.py:233` counts every closed order as settled, including unpaid ones. | B2 | Unit tests: a ¥100 purchase with a ¥30 refund nets ¥70. A friend-accepted WeChat transfer is counted as a P2P transfer. An Alipay closed order counts only if it was paid. |
| **W-11** | No "privacy & how we make money" story | Med | `Landing.tsx:20` has a single line; no business-model text anywhere on the landing | D1 | A landing section in plain words says: what we store, where, who can see it, how to delete it, and how the product is funded. No invented claims. |
| **W-12** | Stamp signature used sparingly and inconsistently | Low | `Stamp` appears in `StatementSheet.tsx:67`, `AuthClient.tsx:215`, `LabelTab.tsx:328`, `TrainingTab.tsx:191`. The upload "done" state is a badge (`UploadQueueItem.tsx:22`), not a stamp. The 404 page has none (`not-found.tsx`). Overview has none. | D0 + D1 + D2 + D3 + D4 | Stamps appear **only** at the approved sites (see §7) with one shared spring. The auth-panel stamps (`AuthClient.tsx:215`) are **not on the approved list**, so D0 should remove them or get them approved. |
| **W-13** | WeChat CSV path skips transfer exclusion | Med | `parse_wechat_csv` (`parse.py:290-347`) never computes `is_transfer`, unlike the XLSX path (`:279`). Credit-card repayments in a WeChat CSV count as spend. | **not in this round.** B2 should fold this into W-06/W-10 if cheap; otherwise next round. | The same transfer rules apply on both WeChat paths (test). |
| **W-14** | Monthly email toggle does nothing | Low | `settings.py:20-24`; the migration comment says "Preference only — no monthly digest email is sent yet" (`20260814030000_notification_prefs.sql:18`) | **not in this round** (the monthly recap email is a later opportunity) | The toggle is hidden, or labeled "coming soon", until sending exists. |

---

## 6. Opportunities

These are ranked by how much they set us apart for expats in China.

| Rank | Opportunity | Why it is ours to win | Round |
|---|---|---|---|
| 1 | **Home-currency view** (rate on each transaction's date) | Expats think in USD, EUR or GBP. No China tool offers this; Western tools don't read our data. | **This round** (W-07) |
| 2 | **Cash flow incl. red packets (红包), AA splits, own-account transfers** | Salary in, rent out, and red packets and split-bill repayments move in both directions. We currently hide all of this (W-06). | **This round** |
| 3 | **Painless import: export guide + bank CSV** | Exporting is the hardest step for a non-Chinese reader (W-09). Bank CSV covers salary cards (W-08). | **This round** |
| 4 | Remittance tracker (money sent home: amount, fee, rate) | A core expat ritual that no competitor models | Later |
| 5 | IIT (Individual Income Tax) helper: deduction categories, annual reconciliation reminders | High value but a regulatory risk. Needs careful sourcing. | Later |
| 6 | Fapiao (发票, official invoice) tagging | Matters for reimbursements and tax | Later |
| 7 | Visa-cycle one-off costs (medical check, permit renewal, flights home) | Spreads lumpy costs across the year | Later |
| 8 | Monthly recap email | The toggle already exists (W-14) | Later |

---

## 7. Decisions log (user decisions, 2026-10-11)

| # | Decision | Applies to |
|---|---|---|
| 1 | Background moves to **grey-green ledger paper**, away from warm cream | W-04, D0 |
| 2 | Display font changes to **Fraunces, `SOFT 100`, `WONK 0`**, replacing Newsreader | W-03, D0 |
| 3 | **Stamps only at the approved sites:** "Imported" (upload row), "Under budget" (a closed month on Overview), "Sorted" (landing demo), "Void" (404 page), plus the existing Label accept stamp and "Trained" | W-12 |
| 4 | **Retune the 12 palette keys' values.** No key or DB change. | W-05 |
| 5 | **Official logos, used small.** The full Alipay logo, including the 支 ("pay") character, is approved as an image exception to the English-only text rule. | W-01, D0 |
| 6 | **Parser fixes approved:** a partial refund negates only the refunded amount; WeChat 朋友已收钱 ("friend has received the money") counts as a P2P transfer; Alipay 交易关闭 ("transaction closed") is ignored only when unpaid | W-10, B2 |
| 7 | **Features this round:** home currency, cash flow, painless import | W-06, W-07, W-08, W-09 |

---

## 8. Not doing (and why)

| Item | Reason |
|---|---|
| Bank sync | Western aggregators (Plaid, GoCardless, SimpleFIN) cover US, EU and UK banks, not mainland Chinese banks or Alipay and WeChat. File upload is the honest path. |
| Native mobile app | Monthly desktop ritual (`PRODUCT.md:29-30`). Responsive web is enough for now. |
| Investments / net worth | Outside the product purpose (`PRODUCT.md:16-20`). Copilot, Monarch and Empower already own it. |
| Social proof / testimonials | None exist. `PRODUCT.md:53-56` forbids fabricating them. Use verifiable mechanism proof instead. |
| Pricing changes | Out of scope for this round |
