/**
 * Recover from a stale tab after a deploy.
 *
 * Each build gives its code-split chunks new hashed filenames. A tab opened
 * before a deploy still runs the old webpack runtime, so when it lazy-loads
 * a tab (next/dynamic) it requests an old chunk that no longer exists →
 * 404 → ChunkLoadError. Reloading picks up the new build.
 *
 * Reloads at most once per 30s per tab (tracked in sessionStorage), so a
 * chunk that is genuinely broken can never cause a reload loop — the error
 * UI is shown instead.
 */
const KEY = 'chunkReloadAt';
const MIN_INTERVAL_MS = 30_000;

export function isChunkLoadError(err: unknown): boolean {
  const e = err as { name?: string; message?: string } | null;
  if (!e) return false;
  return e.name === 'ChunkLoadError' || /Loading (CSS )?chunk [\w-]+ failed/i.test(e.message || '');
}

/** Reload once if `err` is a chunk-load failure. Returns true if reloading. */
export function reloadOnceForChunkError(err: unknown): boolean {
  if (typeof window === 'undefined' || !isChunkLoadError(err)) return false;
  try {
    const last = Number(window.sessionStorage.getItem(KEY) || 0);
    if (Date.now() - last < MIN_INTERVAL_MS) return false;
    window.sessionStorage.setItem(KEY, String(Date.now()));
  } catch {
    // No storage → no loop guard → don't auto-reload.
    return false;
  }
  window.location.reload();
  return true;
}
