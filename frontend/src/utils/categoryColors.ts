/**
 * The category color palette — single source of truth (pure module: no React,
 * safe to import anywhere including the landing page).
 *
 * Users store a palette KEY (e.g. 'blue') on each category, never a hex:
 * every key maps to a light-theme and a dark-theme value (defined as
 * `--cat-<key>` CSS variables in globals.css), so a chosen color stays inside
 * the design system and looks right in both themes.
 *
 * The hexes were validated with the dataviz palette validator (lightness
 * band, chroma floor, contrast >= 3:1 vs both surfaces, per theme). Remaining
 * close CVD pairs are mitigated by secondary encoding: every colored element
 * in the app carries the category NAME as text (badges, legend, swatches).
 *
 * NO purple (design rule, 2026-09-27): violet/indigo/fuchsia were replaced by
 * blue/green/olive — picked with the dataviz validator; the dark chart set
 * passes lightness, chroma, contrast and the normal-vision floor (worst
 * adjacent pair teal/green ΔE 16.1). The remaining CVD FAIL (rose/emerald)
 * predates this change.
 *
 * Must stay in sync with ALLOWED_COLORS in backend/routes/categories.py and
 * the CHECK constraint in migration 20260709120000_add_category_color.sql.
 */
export const CATEGORY_COLORS = [
  { key: 'lime', label: 'Lime', light: '#3f6212', dark: '#4d7c0f' },
  { key: 'blue', label: 'Blue', light: '#1d4ed8', dark: '#2563eb' },
  { key: 'cyan', label: 'Cyan', light: '#0891b2', dark: '#0891b2' },
  { key: 'pink', label: 'Pink', light: '#db2777', dark: '#ec4899' },
  { key: 'amber', label: 'Amber', light: '#a16207', dark: '#d97706' },
  { key: 'sky', label: 'Sky', light: '#075985', dark: '#0284c7' },
  { key: 'emerald', label: 'Emerald', light: '#047857', dark: '#059669' },
  { key: 'rose', label: 'Rose', light: '#9f1239', dark: '#e11d48' },
  { key: 'green', label: 'Green', light: '#467500', dark: '#70a800' },
  { key: 'teal', label: 'Teal', light: '#0d9488', dark: '#0d9488' },
  { key: 'orange', label: 'Orange', light: '#9a3412', dark: '#c2410c' },
  { key: 'olive', label: 'Olive', light: '#707000', dark: '#8a8a3b' },
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

/**
 * Chart-FILL paint for a palette key — deliberately separate from
 * `chartColorForKey`/`--cat-*`. Badges need ~4.5:1 TEXT contrast (why the
 * light-theme `--cat-*` values above are darkened), but a pie/chart fill
 * only needs ~3:1 mark contrast, so reusing the badge-text value there just
 * reads as muddy on a light surface. `--chart-cat-<key>` (globals.css)
 * reuses the already-vivid dark-theme hues for both themes — same identity,
 * no color reassigned per theme, just a fill tuned for fills.
 */
export const chartFillColorForKey = (key: string) => `rgb(var(--chart-cat-${key}))`;
