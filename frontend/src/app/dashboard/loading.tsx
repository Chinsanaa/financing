import Skeleton from '@/components/ui/Skeleton';

/** Route-level skeleton shown while the dashboard bundle/data loads.
 *  Mirrors the Ledger shell (one-row header) and Overview (figure, fact
 *  row, two ruled sections) so nothing jumps when data arrives. */
export default function DashboardLoading() {
  return (
    <div className="min-h-screen" aria-busy="true">
      <span className="sr-only">Loading dashboard…</span>
      <div className="border-b border-edge/15">
        <div className="mx-auto flex h-[52px] w-full max-w-[1800px] items-center gap-6 px-4 sm:px-6 lg:px-8 2xl:px-12">
          <Skeleton className="h-5 w-24" />
          <div className="hidden gap-6 md:flex">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-4 w-20" />
            ))}
          </div>
          <div className="ml-auto flex items-center gap-2">
            <Skeleton className="hidden h-9 w-56 lg:block" />
            <Skeleton className="h-8 w-8" />
            <Skeleton className="h-8 w-8" />
          </div>
        </div>
      </div>
      <div className="mx-auto w-full max-w-[1800px] space-y-10 px-4 py-10 sm:px-6 lg:px-8 2xl:px-12">
        <div>
          <Skeleton className="mb-3 h-4 w-40" />
          <Skeleton className="h-20 w-80" />
        </div>
        <Skeleton className="h-24 w-full" />
        <div className="grid gap-x-14 gap-y-12 lg:grid-cols-[3fr,2fr]">
          <Skeleton className="h-72 w-full" />
          <Skeleton className="h-72 w-full" />
        </div>
      </div>
    </div>
  );
}
