# Design System — "Ledger" (v5)

The visual language of the Financing frontend. **Read this before adding UI.**
Everything is token-driven, so light and dark stay in sync automatically.

- Source of truth for tokens and effects: `frontend/src/app/globals.css` +
  `frontend/tailwind.config.js`
- Components: `frontend/src/components/ui/`
- Product brief for design skills: `PRODUCT.md` (repo root)
- Design skills (installed with Vercel's `npx skills`, committed in
  `.claude/skills/`): **impeccable**, **design-taste-frontend**,
  **redesign-existing-projects**, **apple-design**, **review-animations**,
  **web-design-guidelines**. If a skill contradicts THE RULE (taste-skill
  recommends grain, noise and gradients), THE RULE wins.
- History: v1/v2 dark + electric lime + Space Grotesk; v3 (2026-09-27) flat;
  v4 (2026-10-09): "Ledger" — warm paper + ink, one seal-vermilion accent,
  serif figures, hairline rules instead of cards.
  **v5 (2026-10-11, user decisions): grey-green "ledger paper"** replaces the
  warm cream (all tokens re-derived, light + dark); **Fraunces** (SOFT 100)
  replaces Newsreader; category palette retuned for the green paper;
  `--positive` token; Stamp `size`/`once`; official Alipay / WeChat Pay marks;
  `scripts/design_gate.sh`. Validation: `docs/design/palette-validation-2026-10.txt`.

> ## THE RULE: NO gradients. ONLY solid colors.
> - No `linear-/radial-/conic-gradient` anywhere — backgrounds, text, borders,
>   masks, SVG `<linearGradient>` chart fills (use a solid fill + `fillOpacity`).
>   This includes third-party internals: NumberFlow's digit-fade masks are
>   zeroed in `globals.css` (`--number-flow-mask-*: 0`).
> - No glows or blur effects (`shadow-glow`, colored `drop-shadow` or
>   zero-offset colored `box-shadow`, `blur()` filters — also in entrances —
>   `backdrop-blur`, translucent "glass").
> - **No purple** (violet / indigo / fuchsia / purple / plum) — not as an accent,
>   not in charts, not in the category palette.
> - One flat page background (`bg`); surfaces are one flat color + a hairline.
> - Check before shipping: **`bash scripts/design_gate.sh`** (exit 0 = clean).
>   It greps `frontend/src` for `gradient|backdrop-blur|blur-|blur\(|glass|violet|indigo|fuchsia|purple|plum|shadow-glow|drop-shadow`
>   (case-insensitive; a line containing `design-gate: allow` is skipped — only
>   for comments that explain the rule or a proven-solid legacy name) and fails
>   on any color in `globals.css` / `categoryColors.ts` with OKLCH hue
>   270–335° and chroma > 0.04.

---

## 1. Principles

1. **Paper first.** Light (grey-green ledger paper + green-black ink) is the
   flagship; dark is a quiet green-black "night ledger". Never hardcode a hex/`white`/`black` in a component.
2. **Rules, not boxes.** Sections are separated by hairline rules and
   whitespace. A card exists only when something genuinely floats (popovers,
   the label slip, modals). No card grids of icon + heading + text.
3. **One accent, rationed.** Vermilion marks the primary action on a screen,
   the active nav item, "this month", and the stamp. Everything else is ink.
4. **The chart is the headline.** Numbers are set large in the serif; one
   bold bar beats a donut; every slice is named in ink beside its color.
5. **Color is never the only signal.** Status always carries a word
   ("Over budget", "Near limit") or ▲/▼. A model's *guess* is drawn as an
   **outline**, a confirmed value **solid** — state by line form, not hue.
6. **Motion explains, then gets out of the way** (see §3). Keyboard and
   high-frequency actions never wait on an animation.
7. **No eyebrows.** No uppercase kicker above a heading, no fake "live" dots,
   no icon chips in tinted squares, no 01/02/03 unless sequence is real.

---

## 2. Tokens

Colors are space-separated RGB channels so Tailwind can apply alpha
(`bg-accent/10`, `border-edge/12`). Opacity steps 3/6/8/12 are added in
`tailwind.config.js` (Tailwind's default scale is multiples of 5 — without
them `border-edge/8` silently generates **no CSS**). Never apply an opacity
modifier to an arbitrary `var()` color; make a token. Never invent a token
name (`bg-surface-3` generated nothing for months).

| Token | Use | Light | Dark |
|---|---|---|---|
| `bg` | page (grey-green ledger paper) | `#e8ece4` | `#121814` |
| `surface` | lifted paper: popovers, inputs, label slip | `#f4f6f1` | `#19201b` |
| `surface-2` | inset well (auth brand panel) | `#dbe1d8` | `#232b25` |
| `ink` | text (13.9:1 on paper) | `#18201b` | `#e4eae2` |
| `muted` | secondary text (≥4.85:1 everywhere) | `#56615a` | `#9ba69e` |
| `edge` | hairlines — always low alpha (`/10`–`/25`); `ink/80` for heavy section rules | = ink | = ink |
| `accent` | seal vermilion **fills** (≥3:1) | `#c2371b` | `#e25638` |
| `accent-strong` | vermilion **text** | `#b0301a` | `#ea6a4e` |
| `accent-ink` | text on a vermilion fill (≥5:1) | `#fff8f2` | `#1a0f0b` |
| `positive` | **money in / income** (new in v5; Tailwind `text-positive`) | `#0f6b57` | `#5cc6a6` |
| `danger` | crimson, always with a word | `#9b1c31` | `#f07a86` |
| `success` | ink green (status) | `#2f6b3a` | `#7dba84` |
| `warn` | ochre "approaching" | `#835500` | `#d69e2e` |
| `cyan` | info (slate blue) | `#1f5f7a` | `#6fb3cf` |
| `--cat-*` | 12 category colors (keys stored in DB) | see `categoryColors.ts` | |

`globals.css` stores these as `R G B` channels (hex in a trailing comment).
Every text token is ≥4.5:1 on bg, surface **and** surface-2 in both themes,
computed by script — table in `docs/design/palette-validation-2026-10.txt`.
`positive` (deep teal-green) is deliberately a different hue from `success`
(status green) so "income" never reads as "done".

**Category palette.** Same 12 keys (`lime, blue, cyan, pink, amber, sky,
emerald, rose, green, teal, orange, olive` — changing keys needs a migration,
changing values doesn't). v5 values were found by a constrained OKLCH search
for the grey-green paper (each key held to its hue family, chroma 0.10–0.165,
≥3:1 against page *and* card surface) and validated with the dataviz
validator in picker order: lightness, chroma, CVD separation, normal-vision
floor and 3:1 contrast **all PASS in both themes**. The five green-family
keys are spread by lightness and hue (green darkest, emerald most saturated,
teal toward blue, olive toward yellow, lime/"Moss" between). An all-pairs
check cannot pass for 12 hue-locked colors (worst pair improved from ΔE 3.7
to 7.5), which is why the name is **always** printed in ink beside the color.
Display labels follow the real color (lime → "Moss", amber → "Ochre",
orange → "Rust"). "pink" is held to rose hues (OKLCH 352–8°). The values
live twice — `categoryColors.ts` and the `--cat-*` vars in `globals.css` —
keep them in sync.

**Type.** `font-display` = **Fraunces** (variable: `opsz` 9–144 automatic,
`SOFT` set to **100** for rounded, friendlier terminals, `WONK` 0), loaded
with `next/font/google` (`axes: ['opsz','SOFT','WONK']`). `font-sans` =
**Schibsted Grotesk**. Figures, verified in the built font files:
the Fraunces web subset has **no `tnum`/`lnum`** (lining but proportional
digits) while Schibsted Grotesk has `tnum`; both contain ¥ (U+00A5). So:
- `.num` — money in tables/columns: body face, `tabular-nums lining-nums`.
- `.num-display` — big single figures (hero month total, StatTile/fact
  figures): Fraunces SOFT 100. Never for aligned columns.
Serif headings at `font-normal`/`font-medium`, roman (no italic display),
sentence case. Scale: caption 13px, body 14–15px, section title 24px, page
title 28px, fact figure 32px, month figure 72–96px. (impeccable lists
Fraunces among over-used faces; it is the user's explicit v5 choice.)

**Radius.** `rounded-card` 10px for floating surfaces, `rounded-md` for
controls, `rounded-[2px]` swatches, `rounded-[3px]` stamps, `rounded-pill`
only for kbd/number chips.

**Elevation.** Flat by default; `shadow-card` (ink-tinted, offset + soft
spread, never colored) only on floating things.

**Browser surfaces** are themed: `::selection`, `caret-color`, scrollbars,
`:focus-visible` (2px vermilion outline), `color-scheme`, `theme-color`
meta, `touch-action: manipulation`.

---

## 3. Motion

| Token | Value | Use |
|---|---|---|
| `--ease-out` | `cubic-bezier(0.22, 1, 0.36, 1)` | entrances **and** exits (no ease-in on UI) |
| `--dur-fast` | 150ms | hovers, presses |
| `--dur-base` | 240ms | state changes, dropdowns |
| `--dur-slow` | 280ms | section entrances |
| spring (framer) | `{ type: 'spring', bounce: 0, duration: 0.25–0.35 }` | indicators, menus — critically damped, arrives and stops |
| stamp spring | `bounce: 0.25, duration: 0.42` | **the only bounce**: a stamp is a physical impact |

Rules (apple-design + review-animations):
- Press feedback on pointer-down: `active:scale-[0.97]`, 75ms.
- Dropdowns grow from their trigger (`transformOrigin: top right`), from
  `scale(0.97)`, never `scale(0)`; exits faster than entrances.
- **No animation on keyboard / high-frequency actions:** ⌘K opens with a
  100ms fade and its selection doesn't glide; labeling with 1–9/Enter skips
  the stamp and advances immediately (~40ms).
- Animate `transform`/`opacity` only (`.progress-fill` grows with `scaleX`).
- No ambient loops: the drop zone's ants march only while a file is over it;
  the only loop is training's "working" rule while a run is live.
- Hover styles only on real pointers (`future.hoverOnlyWhenSupported`).
- **Reduced motion is global:** `MotionConfig reducedMotion="user"` in
  `MotionProvider` drops transform animations (opacity still fades); CSS
  collapses keyframes. **Never branch on `useReducedMotion()` while
  rendering server-rendered markup** — it causes hydration errors (#418).
  (Client-only tabs may use it in handlers.)
- Drag: the label slip follows the pointer 1:1, rubber-bands, and decides on
  release from the **projected** position (`offset + velocity × 0.099`), so a
  flick counts like a long drag. Each slip owns its own motion value.

---

## 4. Effects (CSS classes in `globals.css`)

| Class | What it does |
|---|---|
| `.tab-panel` / `.stagger-in` | sections rise 8px in, 40ms apart (280ms) |
| `.progress-fill` | bar grows from 0 (`scaleX`), glides on change |
| `.dash-march` | dashed drop-zone border; marches only under `.is-active` |
| `.skeleton` | solid block, opacity pulse |
| `.kbd` | keyboard hint chip |
| `.num` | tabular lining figures (body face) for columns of money |
| `.num-display` | Fraunces SOFT figures for big single numbers |
| `.section-label` | quiet 13px caption for a chart/column — **not** an eyebrow |
| `.cat-<key>` | sets `--cat` for swatches/bars |

Removed in v4 (do not re-add): `.animate-ping-soft`, `.animate-float`,
`glow-pulse`, `shimmer`, blur in `rise-in`, colored glows on bars/rails, the
NumberFlow gradient masks. v3 removals still stand (`.aurora`, `.grain`,
`.spotlight`, `.glow-border`, `.text-shine`, `.btn-sheen`, `.bg-grid`).

**Stacking-context gotchas:** a transform/filter left on a wrapper traps
`position: fixed` children and popovers — rows that host the color picker
use no transform/overflow; `TabPanel` ends at identity transform.
`FIELD_CLASSES` carries **no width or vertical padding** — Tailwind emits
`w-full`/`py-2.5` after `w-32`/`py-1.5`, so a value there would silently
override the caller's.

---

## 5. Components (`components/ui/`)

| Component | Notes |
|---|---|
| `Card` | `variant="sheet"` (default), `"plain"` (no box, top hairline), `"raised"` (floats). `hover` only darkens the border. `SectionHeader` = serif title + description + action (no label/icon). |
| `StatTile` + `FactRow` + `DeltaChip` | a "fact" (caption, serif figure, footer) — put facts in a `FactRow` (hairline-divided), never in four cards. |
| `Badge` | category: square swatch + ink name; `guess` → outlined swatch. Status tones: `accent`, `success`, `danger`, `warn`, `neutral` (squared label). |
| `Stamp` | the signature: vermilion seal — see **Stamp** below. |
| `Button` | `primary` (vermilion — one per screen), `outline`, `ghost`, `danger` (outlined), `link`; `sm/md/lg`; `loading`. |
| `Segmented` | 2–4 way choice with a sliding ink block (Review mode, theme). |
| `TabBar` / `PillTabs` / `TabPanel` | text nav with a vermilion 2px rule / secondary nav with an ink 1px rule / panel fade-rise. |
| `AccountMenu` | name, Settings, Light/Dark, Sign out (replaced 5 icon buttons + sun/moon toggle). |
| `NotificationBell` | borderless bell, vermilion count, dropdown grows from the bell. |
| `CommandPalette` | ⌘K / Ctrl+K; instant. |
| `EmptyState` | dashed-rule note: what will appear and how. No floating icon. |
| `Input` (`FIELD_CLASSES`), `Switch` (ink when on), `MonthSelect`, `Stepper`, `Toaster`, `Tooltip`, `Skeleton*`, `RollingNumber` (650ms) | |

### Stamp (`ui/Stamp.tsx`)

```tsx
<Stamp label="Imported" />                       // solid = confirmed
<Stamp label="Food" variant="outline" />          // dashed = model guess
<Stamp label="Sorted" size="sm" tilt={-2} delay={0.3} />
<Stamp label="Under budget" once="overview-2026-09" />  // animate once per session
```

Props: `label`, `variant?: 'solid' | 'outline'`, `size?: 'sm' | 'md'`
(default `md`), `tilt?` (resting angle, default −3°), `delay?`, `once?`
(session key: plays the spring only the first time per browser session —
`sessionStorage`, wrapped in try/catch — then renders statically),
`className?`. Under `prefers-reduced-motion` it renders statically. Both
decisions are made in a layout effect after hydration, never during render
(no #418). The spring (`bounce 0.25, 0.42s`) is the app's only bounce.

**Approved stamp sites (exhaustive — never two stamps visible at once):**
1. "Imported" on a finished upload row.
2. "Under budget" on Overview for a closed past month — with `once`.
3. "Sorted" in the landing LiveDemo (replaces the hero StatementSheet stamps).
4. "Void" on the 404 page.
5. LabelTab accept (existing).
6. TrainingTab "Trained" (existing).

### Brand marks (`components/brand/`)

`AlipayLogo`, `WeChatPayLogo` (`size` = height px, `variant?: 'color' | 'mono'`,
`decorative?`) and `FormatBadges` (row "Alipay · WeChat Pay · Bank CSV",
props `size`, `compact`, `variant`). Rules:
- Official artwork only, inline SVG, unmodified paths, official flat colors
  (Alipay `#1677FF`, WeChat Pay `#22AC38`); source URL + download date are in
  each file. No gradients — where an official file has one, the official flat
  variant is used.
- Use **only next to "accepted formats" text** (upload, landing formats line),
  never as decoration, never larger than the adjacent text needs (16–20px).
- The text label is always visible next to each mark.
- Any page that shows the marks carries, in its footer: *"Not affiliated with
  Tencent or Ant Group. WeChat Pay and Alipay are trademarks of their
  respective owners."* (`layout/SiteFooter.tsx` is the shared footer.)
- **The 支 exception:** the Alipay mark contains the character 支 as part of
  its artwork. This is the single user-approved exception to "no Chinese in
  the UI": it is an image (`role="img"`, `aria-label="Alipay"`), never text.
- WeChat Pay green is 2.75:1 on light paper (logos are exempt from WCAG
  1.4.11; the label carries the meaning); use `variant="mono"` for a single-ink
  look.

Deleted in v4: `ThemeToggle`, `ProgressRing`, `utils/celebrate.ts`
(+ `canvas-confetti`), landing `HeroChart`/`DemoStrip`.

---

## 6. Screens

| Screen | Shape |
|---|---|
| Landing | (v5: LiveDemo "Sorted" stamp, shared `SiteFooter`) serif headline "Every yuan, accounted for." → a sample statement whose categories get **stamped** (solid = you, dashed = model) with "Stamp again" → sticky-scroll "Three steps, once a month" (sheets turn on the right; inline on phones) → capability rows (`dl`) → plain close. Lenis smooth scroll here only. Claims = mechanism only. |
| Auth | darker paper well with three stamped rows; form on the page; underline mode tabs. |
| Shell | one-row header: wordmark · text nav · quiet ⌘K field · bell · account. Phones: nav as a second row. |
| Overview | month figure + ▲/▼ · `FactRow` · twelve monthly bars (latest vermilion, dashed average) · "Where it went" stacked bar + ranked rows. |
| Wizard | one ruled 5-step strip (done = ink + check, current = vermilion). |
| Label | raised paper slip; drag right = accept, left = set aside; 1–9/Enter/S; stamp on click/drag accept; "N set aside · bring them back". |
| Review / Reports / Training / Subscriptions / Insights / Action | ruled tables and lists; status words lead; guesses outlined. |
| Budget / 50/30/20 / Savings | `FactRow` + ruled bars; 50/30/20 = one income-wide bar with 50/80 ticks; savings = goal bar with a goal tick. |

---

## 7. Libraries

| Library | Why | Notes |
|---|---|---|
| `framer-motion` | springs, drag, presence, layout | `LazyMotion` + `MotionConfig reducedMotion="user"`; import `m`, never `motion` |
| `lenis` 1.3.26 | landing smooth scroll | landing only; off under reduced motion |
| `@number-flow/react` | rolling digits | gradient masks zeroed |
| `sonner` | toasts | |
| `recharts` | Overview bars | per-tab code split; donut charts removed |

Picked from the user's list and rejected on purpose: GSAP / anime.js (a
second engine for what framer does), Aceternity / Magic UI / React Bits
effects (beams, spotlights, aurora, blur-fade — THE RULE), Bklit charts
(need shadcn + Tailwind v4, gradient fills — its ideas were rebuilt on
Recharts: crosshair-free bars, dashed average). Borrowed: sticky-scroll
layout (Aceternity), animated list stamping (Magic UI), dropdown/segment
transitions (transitions.dev), drag physics (apple-design).

First Load JS (v3 → v4): `/` 132 → 129 kB, `/auth` 206 → 205 kB,
`/dashboard` 211 → 211 kB, `/settings` 188 → 187 kB.

---

## 8. Verifying UI changes

`tsc`/`next build` don't catch visual bugs. Use the harness:

```bash
cd frontend
NEXT_PUBLIC_SUPABASE_URL=https://mockproj.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=mock \
NEXT_PUBLIC_API_URL=http://localhost:9999 npx next build && npx next start -p 3100 &
node scripts/ui-snapshots.cjs ../shots            # every page/tab × light/dark × 1440/390
node scripts/ui-snapshots.cjs ../shots overview   # filter by name
```

It forges an `sb-mockproj-auth-token` cookie and mocks every endpoint; when
a tab shows the error boundary, check the mock shape first (e.g.
`/dashboard/reports`, `{ profile }`). Restart `next start` after every build
— a running server keeps serving its in-memory static pages. Then:

- impeccable's rendered detector: `IMPECCABLE_BROWSER=<chromium --no-sandbox wrapper> .claude/skills/impeccable/scripts/impeccable detect --viewport 390x844 http://localhost:3100/`
  (static file scans of `.tsx` find nothing — scan URLs).
- Emulate `prefers-reduced-motion` and watch for hydration errors (#418).
- `bash scripts/design_gate.sh` (THE RULE + purple-hue check).
