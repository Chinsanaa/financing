/**
 * The category color palette — single source of truth (pure module: no React,
 * safe to import anywhere including the landing page).
 *
 * Users store a palette KEY (e.g. 'violet') on each category, never a hex:
 * every key maps to a light-theme and a dark-theme value (defined as
 * `--cat-<key>` CSS variables in globals.css), so a chosen color stays inside
 * the design system and looks right in both themes.
 *
 * The hexes were validated with the dataviz palette validator (lightness
 * band, chroma floor, contrast >= 3:1 vs both surfaces, per theme). Remaining
 * close CVD pairs are mitigated by secondary encoding: every colored element
 * in the app carries the category NAME as text (badges, legend, swatches).
 *
 * Must stay in sync with ALLOWED_COLORS in backend/routes/categories.py and
 * the CHECK constraint in migration 20260709120000_add_category_color.sql.
 */
export const CATEGORY_COLORS = [
  { key: 'lime', label: 'Lime', light: '#3f6212', dark: '#4d7c0f' },
  { key: 'violet', label: 'Violet', light: '#7c3aed', dark: '#8b5cf6' },
  { key: 'cyan', label: 'Cyan', light: '#0891b2', dark: '#0891b2' },
  { key: 'pink', label: 'Pink', light: '#db2777', dark: '#ec4899' },
  { key: 'amber', label: 'Amber', light: '#a16207', dark: '#d97706' },
  { key: 'sky', label: 'Sky', light: '#075985', dark: '#0284c7' },
  { key: 'emerald', label: 'Emerald', light: '#047857', dark: '#059669' },
  { key: 'rose', label: 'Rose', light: '#9f1239', dark: '#e11d48' },
  { key: 'indigo', label: 'Indigo', light: '#4338ca', dark: '#6366f1' },
  { key: 'teal', label: 'Teal', light: '#0d9488', dark: '#0d9488' },
  { key: 'orange', label: 'Orange', light: '#9a3412', dark: '#c2410c' },
  { key: 'fuchsia', label: 'Fuchsia', light: '#c026d3', dark: '#d946ef' },
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

/** Badge tone class for a palette key (classes defined in globals.css). */
export const toneForKey = (key: string) => `cat-${key}`;

/** Theme-aware paint for charts/swatches (resolves via the CSS variable). */
export const chartColorForKey = (key: string) => `rgb(var(--cat-${key}))`;
