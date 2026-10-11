# Design System — "Ledger" (v4)

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
  **v4 (2026-10-09, user decision): "Ledger"** — warm paper + ink, one
  seal-vermilion accent, serif figures, hairline rules instead of cards.

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
> - Check before shipping: `grep -rnEi "gradient|violet|indigo|fuchsia|purple|backdrop-blur|shadow-glow|blur\(" frontend/src`
>   should only hit comments.

---

## 1. Principles

1. **Paper first.** Light (warm paper + ink) is the flagship; dark is a quiet
   "night ledger". Never hardcode a hex/`white`/`black` in a component.
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
| `bg` | page (paper) | `244 241 234` | `21 20 17` |
| `surface` | lifted paper: popovers, inputs, label slip | `251 250 246` | `29 27 24` |
| `surface-2` | inset well (auth brand panel) | `235 231 222` | `38 36 31` |
| `ink` / `muted` | text (muted 5.3:1 on paper) | `27 26 23` / `104 99 90` | `237 233 224` / `163 157 145` |
| `edge` | hairlines — always low alpha (`/10`–`/25`); `ink/80` for heavy section rules | ink | ink |
| `accent` | seal vermilion fills | `194 55 27` | `226 86 56` |
| `accent-strong` | vermilion **text** | `176 48 26` | `234 106 78` |
| `accent-ink` | text on a vermilion fill (≥5:1) | paper | near-black |
| `danger` | crimson, always with a word | `155 28 49` | `240 122 134` |
| `success` / `warn` / `cyan` (info) | ink green / ochre / slate blue | | |
| `--cat-*` | 12 category colors (keys stored in DB) | see `categoryColors.ts` | |

All text tokens were contrast-checked (≥4.5:1 on bg, surface and wells).

**Category palette.** Same 12 keys (`lime, blue, cyan, pink, amber, sky,
emerald, rose, green, teal, orange, olive` — changing keys needs a migration,
changing values doesn't). Values found by a constrained OKLCH search and
validated with the dataviz validator in stored order, on page *and* card
surfaces: lightness, chroma, CVD separation, normal-vision floor and 3:1
contrast **all PASS in both themes**. Display labels follow the real color
(lime → "Moss", amber → "Ochre", orange → "Rust"). "pink" is held to rose
hues (OKLCH 354–4°) so it never reads as purple. One value per theme serves
swatches, bars and chart fills; the name is always printed in ink beside it.

**Type.** `font-display` = **Newsreader** (variable, optical size axis —
big figures get the fine display cut, table cells the sturdy text cut),
`font-sans` = **Schibsted Grotesk**. Money and counts use `.num` (serif,
lining, tabular). Serif headings at `font-normal`/`font-medium`, roman (no
italic display — flagged by impeccable as the AI-startup hero cliché),
sentence case. Scale: caption 13px, body 14–15px, section title 24px,
page title 28px, fact figure 32px, month figure 72–96px.

**Radius.** `rounded-card` 10px for floating surfaces, `rounded-md` for
controls, `rounded-[2px]` swatches, `rounded-[3px]` stamps, `rounded-pill`
only for kbd/number chips.

**Elevation.** Flat by default; `shadow-card` (warm-ink, offset + soft blur,
never colored) only on floating things.

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
| `.num` | serif tabular lining figures |
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
| `Stamp` | the signature: vermilion seal, `solid` (confirmed) / `outline` (dashed, model guess), lands tilted with the one bouncy spring. Landing hero, auth panel, label accept, training success (replaced confetti). |
| `Button` | `primary` (vermilion — one per screen), `outline`, `ghost`, `danger` (outlined), `link`; `sm/md/lg`; `loading`. |
| `Segmented` | 2–4 way choice with a sliding ink block (Review mode, theme). |
| `TabBar` / `PillTabs` / `TabPanel` | text nav with a vermilion 2px rule / secondary nav with an ink 1px rule / panel fade-rise. |
| `AccountMenu` | name, Settings, Light/Dark, Sign out (replaced 5 icon buttons + sun/moon toggle). |
| `NotificationBell` | borderless bell, vermilion count, dropdown grows from the bell. |
| `CommandPalette` | ⌘K / Ctrl+K; instant. |
| `EmptyState` | dashed-rule note: what will appear and how. No floating icon. |
| `Input` (`FIELD_CLASSES`), `Switch` (ink when on), `MonthSelect`, `Stepper`, `Toaster`, `Tooltip`, `Skeleton*`, `RollingNumber` (650ms) | |

Deleted in v4: `ThemeToggle`, `ProgressRing`, `utils/celebrate.ts`
(+ `canvas-confetti`), landing `HeroChart`/`DemoStrip`.

---

## 6. Screens

| Screen | Shape |
|---|---|
| Landing | serif headline "Every yuan, accounted for." → a sample statement whose categories get **stamped** (solid = you, dashed = model) with "Stamp again" → sticky-scroll "Three steps, once a month" (sheets turn on the right; inline on phones) → capability rows (`dl`) → plain close. Lenis smooth scroll here only. Claims = mechanism only. |
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
- The rule grep at the top of this file.
