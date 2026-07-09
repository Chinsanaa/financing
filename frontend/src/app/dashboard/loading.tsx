import Skeleton, { SkeletonCard, SkeletonChart } from '@/components/ui/Skeleton';

/** Route-level skeleton shown while the dashboard bundle/data loads. */
export default function DashboardLoading() {
  return (
    <div className="min-h-screen">
      <div className="border-b border-edge/8">
        <div className="mx-auto flex w-full max-w-[1800px] items-center justify-between px-4 py-4 sm:px-6 lg:px-8 2xl:px-12">
          <Skeleton className="h-7 w-32" />
          <div className="flex gap-3">
            <Skeleton className="h-9 w-9 rounded-full" />
            <Skeleton className="h-9 w-24 rounded-full" />
          </div>
        </div>
        <div className="mx-auto flex w-full max-w-[1800px] gap-2 px-4 pb-3 sm:px-6 lg:px-8 2xl:px-12">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-8 w-24" />
          ))}
        </div>
      </div>
      <div className="mx-auto w-full max-w-[1800px] px-4 py-8 sm:px-6 lg:px-8 2xl:px-12">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
        {/* Mirrors StatsTab's real chart grid proportions. */}
        <div className="mt-6 grid gap-5 lg:grid-cols-[3fr,2fr]">
          <SkeletonChart />
          <SkeletonChart />
        </div>
      </div>
    </div>
  );
}
