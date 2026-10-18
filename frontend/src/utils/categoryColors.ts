/**
 * The category color palette — single source of truth (pure module: no React,
 * safe to import anywhere including the landing page).
 *
 * Users store a palette KEY (e.g. 'blue') on each category, never a hex:
 * every key maps to a light-theme and a dark-theme value (defined as
 * `--cat-<key>` CSS variables in globals.css), so a chosen color stays inside
 * the design system and looks right in both themes.
 *
 * Ledger palette (design system v5, 2026-10-11): muted "ink" hues retuned
 * for the grey-green ledger paper (light) and the green-black night ledger
 * (dark). Found with a constrained OKLCH search (each key held to its hue
 * family, OKLCH chroma 0.10-0.165, >= 3:1 against both page and card
 * surface), maximising separation, then checked with the dataviz validator
 * in this (picker) order: lightness band, chroma floor, CVD separation,
 * normal-vision floor and contrast all PASS in both themes. The five
 * green-family keys (lime/Moss, green, emerald, teal, olive) are spread by
 * lightness and hue so none disappears into the green paper. An all-pairs
 * check cannot pass with 12 hue-locked colors; every colored element
 * therefore prints the category NAME (in ink) beside it.
 * Results: docs/design/palette-validation-2026-10.txt.
 *
 * No OKLCH hue 270-335 (design rule, 2026-09-27; scripts/design_gate.sh):
 * "pink" is held to rose-pink hues (OKLCH 352-8 deg) so it never drifts
 * toward magenta.
 *
 * Must stay in sync with ALLOWED_COLORS in backend/routes/categories.py and
 * the CHECK constraint in migration 20260709120000_add_category_color.sql
 * (only the KEYS are stored — changing values here needs no migration).
 */
export const CATEGORY_COLORS = [
  { key: 'lime', label: 'Moss', light: '#617c35', dark: '#727f04' },
  { key: 'blue', label: 'Blue', light: '#2d5296', dark: '#3165c7' },
  { key: 'cyan', label: 'Cyan', light: '#2290af', dark: '#249fb9' },
  { key: 'pink', label: 'Pink', light: '#7f3351', dark: '#bd507b' },
  { key: 'amber', label: 'Ochre', light: '#a96200', dark: '#c87c06' },
  { key: 'sky', label: 'Sky', light: '#0074ae', dark: '#0a86c4' },
  { key: 'emerald', label: 'Emerald', light: '#00984a', dark: '#0b9646' },
  { key: 'rose', label: 'Rose', light: '#9a4752', dark: '#d1747d' },
  { key: 'green', label: 'Green', light: '#356000', dark: '#1e7927' },
  { key: 'teal', label: 'Teal', light: '#15937c', dark: '#05a990' },
  { key: 'orange', label: 'Rust', light: '#a43203', dark: '#9f573a' },
  { key: 'olive', label: 'Olive', light: '#95860a', dark: '#979845' },
] as const;

export type CategoryColorKey = (typeof CATEGORY_COLORS)[number]['key'];

export const CATEGORY_COLOR_KEYS: readonly CategoryColorKey[] = CATEGORY_COLORS.map((c) => c.key);
export const CATEGORY_COLOR_KEY_SET: ReadonlySet<string> = new Set<string>(CATEGORY_COLOR_KEYS);

/**
 * Deterministic fallback for categories with no chosen color (and for the
 * static landing-page demos). Same hash the old 5-entry Badge palette used,
 * now cycling all 12 keys. A hash pick can coincide with a chosen color —
 * explicitly picking colors resolves that; making the hash "skip taken keys"
 * would reshuffle every auto color whenever a selection changes.
 */
export function hashCategoryKey(name: string): CategoryColorKey {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = (hash * 31 + name.charCodeAt(i)) | 0;
  return CATEGORY_COLOR_KEYS[Math.abs(hash) % CATEGORY_COLOR_KEYS.length];
}

/** Class that sets `--cat` for a palette key (classes defined in globals.css). */
export const toneForKey = (key: string) => `cat-${key}`;

/** Theme-aware paint for charts/swatches (resolves via the CSS variable). */
export const chartColorForKey = (key: string) => `rgb(var(--cat-${key}))`;

