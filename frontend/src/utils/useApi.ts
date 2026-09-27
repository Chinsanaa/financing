'use client';

import { useCallback, useEffect, useState } from 'react';
import { api } from './api';
import { clearApiCache, readCached, writeCached, dropCached } from './apiCache';

/**
 * Tiny stale-while-revalidate data hook (no external deps).
 *
 * - First mount of a path: fetch + spinner.
 * - Re-mount (tab switch back) or page reload in the same tab: render the
 *   cached data instantly, refresh in the background. The cache lives in
 *   memory and is mirrored to sessionStorage (see apiCache.ts), so a reload
 *   doesn't start from a blank spinner.
 * - Concurrent requests for the same path share one network call (e.g.
 *   OnboardingTour and StatsTab both mount with /dashboard/summary).
 * - Mutations call `invalidate(prefix)` and/or `reload()`.
 */

export { clearApiCache };

// Mounted useApi(path) instances register a background-revalidate callback here,
// keyed by their exact path, so invalidate() can reach components that never
// unmount (e.g. OnboardingTour) and not just the caller that mutated data.
const subscribers = new Map<string, Set<() => void>>();
// In-flight GETs by path — a second caller awaits the first's promise.
const inflight = new Map<string, Promise<unknown>>();

export function invalidate(prefix = '', opts?: { except?: string[] }): void {
  const except = opts?.except || [];
  const skip = (path: string) => except.some((p) => path.startsWith(p));
  dropCached((key) => key.startsWith(prefix) && !skip(key));
  // A GET that started before the mutation may carry pre-mutation data —
  // don't let the refetches below piggyback on it.
  Array.from(inflight.keys()).forEach((key) => {
    if (key.startsWith(prefix) && !skip(key)) inflight.delete(key);
  });
  subscribers.forEach((callbacks, path) => {
    if (path.startsWith(prefix) && !skip(path)) callbacks.forEach((cb) => cb());
  });
}

function fetchShared(path: string): Promise<unknown> {
  const pending = inflight.get(path);
  if (pending) return pending;
  const request = api
    .get(path)
    .then((res) => {
      writeCached(path, res.data);
      return res.data;
    })
    .finally(() => inflight.delete(path));
  inflight.set(path, request);
  return request;
}

export function useApi<T>(path: string | null) {
  const [data, setData] = useState<T | null>(() => (path ? (readCached(path) as T | undefined) ?? null : null));
  const [loading, setLoading] = useState<boolean>(() => !!path && readCached(path) === undefined);
  const [error, setError] = useState('');

  const load = useCallback(
    async (background = false) => {
      if (!path) return;
      if (!background) setLoading(true);
      try {
        setData((await fetchShared(path)) as T);
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
    const cached = readCached(path);
    if (cached !== undefined) {
      setData(cached as T);
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
