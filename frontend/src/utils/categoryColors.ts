/**
 * The category color palette — single source of truth (pure module: no React,
 * safe to import anywhere including the landing page).
 *
 * Users store a palette KEY (e.g. 'blue') on each category, never a hex:
 * every key maps to a light-theme and a dark-theme value (defined as
 * `--cat-<key>` CSS variables in globals.css), so a chosen color stays inside
 * the design system and looks right in both themes.
 *
 * Ledger palette (design system v4, 2026-10-09): muted "ink" hues tuned
 * for warm paper (light) and the night ledger (dark). Found with a search
 * over OKLCH constrained to each key's hue family, then checked with the
 * dataviz validator (validate_palette.js), in stored key order, against
 * both page and card surfaces: lightness band, chroma floor, CVD separation,
 * normal-vision floor and 3:1 contrast all PASS in both themes. Every
 * colored element still prints the category NAME (in ink) beside the color.
 *
 * NO purple (design rule, 2026-09-27): "pink" is held to rose-pink hues
 * (OKLCH 354–4°) so it never drifts toward magenta/plum.
 *
 * Must stay in sync with ALLOWED_COLORS in backend/routes/categories.py and
 * the CHECK constraint in migration 20260709120000_add_category_color.sql
 * (only the KEYS are stored — changing values here needs no migration).
 */
export const CATEGORY_COLORS = [
  { key: 'lime', label: 'Moss', light: '#597123', dark: '#678b2e' },
  { key: 'blue', label: 'Blue', light: '#2658a9', dark: '#2568bf' },
  { key: 'cyan', label: 'Cyan', light: '#0a94af', dark: '#0b9daa' },
  { key: 'pink', label: 'Pink', light: '#a83a61', dark: '#b2426f' },
  { key: 'amber', label: 'Ochre', light: '#ae7324', dark: '#b08739' },
  { key: 'sky', label: 'Sky', light: '#2780ad', dark: '#1f90d2' },
  { key: 'emerald', label: 'Emerald', light: '#0b6730', dark: '#38a962' },
  { key: 'rose', label: 'Rose', light: '#c16963', dark: '#ad4e53' },
  { key: 'green', label: 'Green', light: '#386506', dark: '#659200' },
  { key: 'teal', label: 'Teal', light: '#1b9a89', dark: '#0ba6a6' },
  { key: 'orange', label: 'Rust', light: '#9a4019', dark: '#a9552e' },
  { key: 'olive', label: 'Olive', light: '#91851b', dark: '#9e9527' },
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

/** Same paint for chart fills (kept as a separate name for call sites —
 *  in v4 one value per theme serves swatches, bars and fills). */
export const chartFillColorForKey = (key: string) => `rgb(var(--cat-${key}))`;
