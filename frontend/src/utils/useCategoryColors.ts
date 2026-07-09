'use client';

import { useMemo } from 'react';
import { useApi } from './useApi';
import {
  CATEGORY_COLOR_KEY_SET,
  CategoryColorKey,
  chartColorForKey,
  hashCategoryKey,
  toneForKey,
} from './categoryColors';

interface CategoryRow {
  id: string;
  name: string;
  color?: string | null;
}

/**
 * Resolve category names to their user-chosen colors, everywhere.
 *
 * Reads /categories/ through useApi's shared cache, so every consumer sees the
 * same data and a color change propagates site-wide via
 * invalidate('/categories'). Dashboard endpoints return category NAMES (unique
 * per user), so name is a sufficient key; unknown names and categories with no
 * chosen color fall back to the deterministic hash.
 */
export function useCategoryColors() {
  const { data } = useApi<{ categories: CategoryRow[] }>('/categories/');

  return useMemo(() => {
    const byName = new Map<string, CategoryColorKey>();
    for (const c of data?.categories || []) {
      const key =
        c.color && CATEGORY_COLOR_KEY_SET.has(c.color)
          ? (c.color as CategoryColorKey)
          : hashCategoryKey(c.name);
      byName.set(c.name, key);
    }
    const keyFor = (name: string) => byName.get(name) ?? hashCategoryKey(name);
    return {
      keyFor,
      toneFor: (name: string) => toneForKey(keyFor(name)),
      chartColorFor: (name: string) => chartColorForKey(keyFor(name)),
    };
  }, [data]);
}
