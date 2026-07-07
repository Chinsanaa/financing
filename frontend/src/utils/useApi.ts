'use client';

import { useCallback, useEffect, useState } from 'react';
import { api } from './api';

/**
 * Tiny stale-while-revalidate data hook (no external deps).
 *
 * - First mount of a path: fetch + spinner.
 * - Re-mount (tab switch back): render the cached data instantly, refresh
 *   in the background. Kills the "every tab switch refetches with a
 *   full-page spinner" behavior.
 * - Mutations call `invalidate(prefix)` and/or `reload()`.
 */

const cache = new Map<string, unknown>();
// Mounted useApi(path) instances register a background-revalidate callback here,
// keyed by their exact path, so invalidate() can reach components that never
// unmount (e.g. OnboardingChecklist) and not just the caller that mutated data.
const subscribers = new Map<string, Set<() => void>>();

export function invalidate(prefix = ''): void {
  Array.from(cache.keys()).forEach((key) => {
    if (key.startsWith(prefix)) cache.delete(key);
  });
  subscribers.forEach((callbacks, path) => {
    if (path.startsWith(prefix)) callbacks.forEach((cb) => cb());
  });
}

export function useApi<T>(path: string | null) {
  const [data, setData] = useState<T | null>(
    path && cache.has(path) ? (cache.get(path) as T) : null
  );
  const [loading, setLoading] = useState<boolean>(!!path && !cache.has(path));
  const [error, setError] = useState('');

  const load = useCallback(
    async (background = false) => {
      if (!path) return;
      if (!background) setLoading(true);
      try {
        const res = await api.get(path);
        cache.set(path, res.data);
        setData(res.data as T);
        setError('');
      } catch (err: any) {
        setError(err?.response?.data?.detail || 'Failed to load data');
      } finally {
        setLoading(false);
      }
    },
    [path]
  );

  useEffect(() => {
    if (!path) return;
    if (cache.has(path)) {
      setData(cache.get(path) as T);
      setLoading(false);
      load(true); // revalidate in the background
    } else {
      load();
    }
  }, [path, load]);

  useEffect(() => {
    if (!path) return;
    const refetch = () => load(true);
    if (!subscribers.has(path)) subscribers.set(path, new Set());
    subscribers.get(path)!.add(refetch);
    return () => {
      subscribers.get(path)?.delete(refetch);
    };
  }, [path, load]);

  return { data, setData, loading, error, reload: load };
}
