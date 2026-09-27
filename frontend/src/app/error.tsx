'use client';

import { useEffect, useState } from 'react';
import { Alert } from '@/components/ui-feedback';
import { reloadOnceForChunkError } from '@/utils/chunkReload';

/**
 * App-wide error boundary (Next.js `error.tsx`). Previously any render error
 * fell through to Next's bare "Application error" page.
 *
 * A ChunkLoadError (tab left open across a deploy) reloads once to fetch the
 * new build; anything else shows a message with retry options.
 */
export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  const [reloading, setReloading] = useState(false);

  useEffect(() => {
    if (reloadOnceForChunkError(error)) setReloading(true);
    else console.error(error);
  }, [error]);

  if (reloading) return null;

  return (
    <div className="mx-auto flex min-h-[60vh] max-w-md flex-col justify-center gap-4 px-4">
      <Alert kind="error">
        Something went wrong loading this page. If the site was just updated, reloading usually fixes it.
      </Alert>
      <div className="flex gap-3">
        <button
          onClick={() => window.location.reload()}
          className="rounded-pill bg-accent px-4 py-2 text-sm font-medium text-accent-ink"
        >
          Reload page
        </button>
        <button
          onClick={reset}
          className="rounded-pill border border-edge/20 px-4 py-2 text-sm text-ink"
        >
          Try again
        </button>
      </div>
    </div>
  );
}
