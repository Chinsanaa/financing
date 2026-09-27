/**
 * GET-response cache for useApi: an in-memory Map mirrored to sessionStorage.
 *
 * sessionStorage (not localStorage) on purpose: it's per-tab and gone when
 * the tab closes, so spending data doesn't linger on a shared computer. It's
 * also cleared on sign-out and on any 401 (see api.ts). Every storage access
 * is wrapped — private mode / disabled storage / quota errors just fall back
 * to the in-memory cache.
 */

// Bump when a cached response shape changes so old entries are ignored.
const PREFIX = 'apiCache:v1:';

const memory = new Map<string, unknown>();

function storage(): Storage | null {
  try {
    return typeof window === 'undefined' ? null : window.sessionStorage;
  } catch {
    return null;
  }
}

export function readCached(path: string): unknown | undefined {
  if (memory.has(path)) return memory.get(path);
  try {
    const raw = storage()?.getItem(PREFIX + path);
    if (raw == null) return undefined;
    const value = JSON.parse(raw);
    memory.set(path, value);
    return value;
  } catch {
    return undefined;
  }
}

export function writeCached(path: string, value: unknown): void {
  memory.set(path, value);
  try {
    storage()?.setItem(PREFIX + path, JSON.stringify(value));
  } catch {
    // Quota exceeded or storage unavailable — the in-memory copy still works.
  }
}

export function dropCached(match: (path: string) => boolean): void {
  Array.from(memory.keys()).forEach((key) => {
    if (match(key)) memory.delete(key);
  });
  const store = storage();
  if (!store) return;
  try {
    for (let i = store.length - 1; i >= 0; i--) {
      const key = store.key(i);
      if (key?.startsWith(PREFIX) && match(key.slice(PREFIX.length))) store.removeItem(key);
    }
  } catch {
    // ignore
  }
}

/** Forget every cached response (sign-out, expired session). */
export function clearApiCache(): void {
  dropCached(() => true);
}
