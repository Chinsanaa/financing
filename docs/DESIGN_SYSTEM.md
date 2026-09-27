# Design System — "Aurora Lime" (v2)

The visual language of the Financing frontend. **Read this before adding UI.**
Everything is token-driven, so light and dark stay in sync automatically.

- Source of truth for tokens and effects: `frontend/src/app/globals.css` +
  `frontend/tailwind.config.js`
- Components: `frontend/src/components/ui/`
- v2 (Session 69, 2026-09-27) kept the v1 identity (dark-first, electric lime,
  Space Grotesk) and layered on depth, motion and a few signature moments.

---

## 1. Principles

1. **Dark is the flagship; light is a tasteful inversion.** Design both at once —
   never hardcode a hex/`white`/`black` in a component. Use tokens.
2. **Motion explains, it doesn't decorate.** Every animation answers "what just
   changed?" (a number rolled because the month changed, a card flew right
   because you labeled it). Repeated-work screens (Label, Reports) stay calm.
3. **One hero per view.** The orbiting `glow` border, `text-shine` and confetti
   are rationed: at most one each per screen, or they stop meaning anything.
4. **Color is never the only signal.** Status colors always come with a word
   or icon ("Over", ▲/▼, a meter + a number).
5. **Reduced motion is respected everywhere** — a global rule in `globals.css`
   collapses animations (and zeroes stagger delays); NumberFlow, ProgressRing,
   WordReveal and `celebrate()` also check it themselves.

---

## 2. Tokens

Colors are space-separated RGB channels so Tailwind can apply alpha:
`bg-accent/12`, `border-edge/8`.

| Token | Use | Dark | Light |
|---|---|---|---|
| `bg` | page background | `10 10 15` | `250 250 248` |
| `surface` / `surface-2` | cards / insets, inputs | `19 19 24` / `27 27 35` | white / `241 241 243` |
| `ink` / `muted` | primary / secondary text | near-white / gray | near-black / gray |
| `edge` | borders & hairlines — **always at low alpha** (`/8`, `/10`, `/15`) | white | near-black |
| `accent` | electric lime fills, glows | `200 255 61` | `132 204 22` |
| `accent-strong` | lime **text** (contrast-safe on light) | = accent | `77 124 15` |
| `accent-ink` | text on an accent fill | near-black | near-black |
| `violet`, `cyan` | secondary glows / info | | |
| `success`, `danger` | good / bad status | | |
| `warn` | "approaching" amber status (added v2) | `217 119 6` | `180 83 9` |
| `--cat-*` / `--chart-cat-*` | 12 user-selectable category colors (badge text / chart fills) | see `categoryColors.ts` | |

**Opacity steps.** Tailwind's default scale is multiples of 5; v2 adds
`3, 6, 8, 12` (`tailwind.config.js → theme.extend.opacity`). Before that,
`border-edge/8` and `bg-accent/12` silently generated **no CSS** and every card
border fell back to Tailwind's default light gray. If you need another step,
add it there — and never use an opacity modifier on an arbitrary `var()` color
(`bg-[color:var(--x)]/10` generates nothing in Tailwind 3); make a token instead.

**Type.** `font-display` = Space Grotesk (headings, numbers), `font-sans` = Inter
(body). Numbers use `tabular-nums`. Scale: section label 11px uppercase tracked
(`.section-label`), body 14px, card title 18px, page title 24–28px, KPI 30px,
hero figure 48–60px.

**Radius.** `rounded-card` (16px) for surfaces, `rounded-pill` for buttons /
chips / tabs, `rounded-lg`/`xl` for inner elements and icon chips.

**Elevation.** Flat surface + hairline border by default; `shadow-card` for
lifted/hovered/floating things; `shadow-glow` (lime) only for accent elements.

---

## 3. Motion tokens

| Token | Value | Use |
|---|---|---|
| `--ease-out` | `cubic-bezier(0.22, 1, 0.36, 1)` | entrances (expo-out) |
| `--ease-in` | `cubic-bezier(0.55, 0, 1, 0.45)` | exits |
| `--dur-fast` | 150ms | hovers, presses |
| `--dur-base` | 240ms | state changes |
| `--dur-slow` | 480ms | entrances, charts |
| spring (framer) | `stiffness 500, damping 40` | tab indicators, shared-layout pills |

Exits are faster than entrances (~60%). Stagger step: 55ms.

---

## 4. Effects (CSS classes in `globals.css`)

| Class | What it does | Where |
|---|---|---|
| `.aurora` + `.grain` | fixed drifting lime/violet glows + film grain behind the page | dashboard, settings, auth, landing (mount once per page; content above it needs `relative z-[1]`) |
| `.spotlight` | soft glow + lit border that follow the pointer (`--mx/--my` via `trackSpotlight`) | `<Card hover>` / `<Card spotlight>` |
| `.glow-border` | a lime→violet light orbits the card edge | `<Card glow>` — Overview hero, auth card, landing CTA, ⌘K palette, Training while running |
| `.text-shine` | slow shimmer across gradient text | one headline word per page |
| `.stagger-in` | direct children rise in 55ms apart | automatic on every tab's top-level sections (`.tab-panel`), tables, settings |
| `.progress-fill` | bar grows from 0, glides on change, one light sweep | `ProgressBar`, custom mini-bars |
| `.btn-sheen` | light sweep across the primary button on hover | `Button variant="primary"` |
| `.dash-march` | marching-ants SVG border; fast while `.is-active` | upload drop zone |
| `.animate-float`, `.animate-ping-soft` | idle float / radiating ring | empty states, live dots |
| `.kbd` | keyboard-hint chip | ⌘K, label shortcuts |

**Stacking-context gotchas (learned the hard way):**
- `.spotlight` / `.glow-border` set `isolation: isolate`, and hover lifts use
  `transform` — both trap absolutely-positioned popovers (e.g. the category
  color picker) under later siblings. Don't use `hover`/`spotlight` on cards
  that contain popovers.
- A non-`none` `filter` or `transform` left on a wrapper makes it the
  containing block for `position: fixed` children (modals). `TabPanel` ends its
  blur with `transitionEnd: { filter: 'none' }` for this reason; CSS entrances
  use `animation-fill-mode: backwards`, never `both`.
- `overflow: hidden` clips at the padding box, so ring effects sit at
  `inset: 0`, not `-1px`.

---

## 5. Components (`components/ui/`)

| Component | Notes |
|---|---|
| `Card` | `glass`, `hover` (lift + spotlight), `spotlight`, `glow`. `SectionHeader` = eyebrow with live dot + title + optional `description`, `icon`, `action`. |
| `StatTile` + `DeltaChip` | KPI tile: label, icon chip, big `RollingNumber`, footer. `tone` colors the number only. `DeltaChip pct goodWhenDown` for ▲/▼ % chips. |
| `RollingNumber` | odometer digits (`@number-flow/react`); rolls up the first time it scrolls into view and on every change. `currency` = whole yuan, sign before ¥. |
| `ProgressBar` (`ui-feedback.tsx`) | `fillColor`, `height`, `marker` (target tick, e.g. 50/30/20), `label` (a11y). |
| `ProgressRing` | SVG gauge that springs to `percent`; children render in the middle. |
| `Button` | `primary` (sheen + glow), `outline`, `ghost`, `danger`; `sm/md/lg`; `loading`. |
| `TabBar` / `PillTabs` / `TabPanel` | TabBar: hover pill glides between tabs + glowing active underline. PillTabs: shared-layout pill, optional icons. TabPanel: blur-rise + section stagger. |
| `CommandPalette` | ⌘K / Ctrl+K launcher. Commands are declared in `DashboardClient`. |
| `EmptyState` | floating icon with ping ring over a faint glow; always say what will appear and how. |
| `MonthSelect` | pill month picker (Budget, 50/30/20). |
| `Toaster` | sonner host, follows our class theme. `toast.success()` for completed actions; errors stay inline (`<Alert kind="error">`) next to what failed. |
| `ThemeToggle` | sun/moon swap animation; `utils/theme.ts` exposes `toggleTheme()` + `useIsDark()` (stays in sync with ⌘K). |
| `Skeleton*` | shimmer placeholders that mirror the real layout (avoid layout shift). |

Utilities: `utils/spotlight.ts` (`trackSpotlight`), `utils/celebrate.ts`
(confetti — **milestones only**, currently a successful training run),
`utils/theme.ts`.

---

## 6. Signature moments (where the "wow" lives)

| Screen | Moment |
|---|---|
| Landing | word-by-word blur headline + shimmering "goes."; hero mockup tilts toward the cursor with floating "auto-categorized" chips; grid lights up under the pointer; merchant marquee (pauses on hover); bento features; glowing CTA |
| Auth | glass card with orbiting glow; brand-panel spending line draws itself in |
| Dashboard shell | aurora backdrop; ⌘K palette; spotlight tab bar; restored Planning sub-tabs |
| Overview | greeting + last month's spend rolling in with ▲/▼ vs the prior month; gradient area chart; donut ↔ legend hover sync with center label |
| Wizard | connected stepper whose rail fills with progress; step content slides in the direction of travel |
| Upload | marching-ants drop zone that speeds up + glows on drag-over |
| Label | stacked-deck card that flies off when labeled; **keyboard: 1–9 pick a category, Enter accepts, S skips** |
| Training | "thinking" pulse while a run is live; confetti + toast on success; metrics roll in |
| Budget / Savings | KPI tiles (income, budgeted, spent, left); savings-goal ring gauge |
| 50/30/20 | donut center shows % of income; target ticks on each bucket bar |
| Subscriptions / Insights / Action | monogram cards; current-vs-average bars; severity rails and an "All clear" state |

---

## 7. Libraries

| Library | Why | Notes |
|---|---|---|
| `framer-motion` (existing) | layout animations, springs, presence | lazy-loaded via `LazyMotion` (`MotionProvider`) — always import `m`, never `motion` |
| `@number-flow/react` | accessible rolling digits | |
| `sonner` | toasts | mounted once in the root layout |
| `canvas-confetti` | milestone celebration | dynamic import — not in any bundle until it fires |
| `recharts` (existing) | charts | per-tab code split |

Measured `next build` First Load JS, before → after v2: `/` 130 → 136 kB,
`/auth` 205 → 206 kB, `/dashboard` 207 → 211 kB, `/settings` 188 kB (flat).

Patterns were inspired by the copy-paste libraries Skiper UI and Vengeance UI
(spotlight nav, glow-border cards, animated numbers, staggered grids,
marquees). We re-implemented them against our tokens instead of copying their
source — most Skiper components are paid, and our versions stay theme-aware.

---

## 8. Verifying UI changes

`npx tsc --noEmit` and `next build` don't catch visual bugs (the missing
opacity classes above passed both for months). For the logged-in dashboard,
build with mock env vars (`NEXT_PUBLIC_SUPABASE_URL=https://mockproj.supabase.co`,
`NEXT_PUBLIC_API_URL=http://localhost:9999`), set a fake
`sb-mockproj-auth-token` cookie, and serve mock JSON for every endpoint with
Playwright's `context.route()` — then screenshot each `?tab=` in both themes
and at 390px width. Scroll the page before full-page shots, or
`whileInView` / roll-up content won't have triggered.
