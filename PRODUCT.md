# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
English speakers living in China whose spending is split across Alipay and
WeChat Pay. They export statement CSVs, usually once a month, and want one
honest, categorized view of where the money went. The project owner is the
first user; signup is open to anyone.

## Product Purpose
Merge Alipay + WeChat statements into one timeline, categorize every
transaction automatically, and show spending by category, over time and by
merchant. It should get better with use instead of needing re-categorization
every month. Success is a monthly review that takes minutes, not an evening
in a spreadsheet.

## Positioning
Each account trains its **own** classifier on its own labels (TF-IDF /
Model2Vec + Logistic Regression), built for mixed Chinese/English merchant
text (segmented with jieba). The app learns *your* merchants instead of
applying generic rules.

## Operating Context
- Monthly ritual: export CSV/Excel from Alipay and WeChat → upload →
  label the few merchants the model is unsure about → review → read the month.
- Repeated-work screens (Label, Review, Reports) are used in long sessions
  with the keyboard (1–9 / Enter / S, ⌘K).
- Planning: budgets, 50/30/20 split, savings goal, subscriptions, insights,
  action plan.

## Capabilities and Constraints
- Next.js 14 frontend (Vercel), FastAPI backend (Render), Supabase auth/data.
- The UI is English only. Chinese merchant text is shown translated.
- Currency is CNY (¥).
- Category colors are user-selectable from 12 fixed keys stored in the DB
  (`lime, blue, cyan, pink, amber, sky, emerald, rose, green, teal, orange,
  olive`). The keys can't change without a migration; their rendered values can.

## Brand Commitments
- Name: "Financing." (wordmark with a period, no logo square).
- **THE RULE (binding, from the owner):** no gradients, only solid colors. No
  glows, no blur effects, no glass, no aurora/grain/grid backgrounds, no
  purple anywhere (including charts and categories). One flat page background.
  This overrides any design skill's advice.
- Don't make it look AI-generated or templated.

## Evidence on Hand
- No testimonials, user counts, press or benchmarks exist. Never fabricate
  them. The landing page claims only the mechanism, shown with a realistic
  demo statement (translated merchants such as Luckin Coffee, Didi, Meituan,
  Shanghai Metro).

## Product Principles
1. Honest over impressive: never invent a number, a trust threshold or a claim.
2. The user's own data and labels are the product; keep them private per account.
3. Calm for repeated work: speed and scanability beat spectacle in the app.
4. Explain what changed: motion and feedback answer "what just happened?".

## Accessibility & Inclusion
- Respect `prefers-reduced-motion` everywhere.
- Color is never the only signal: status always pairs with a word or an icon.
- Full keyboard paths for labeling and navigation.
