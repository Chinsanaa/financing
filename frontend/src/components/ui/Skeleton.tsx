/** Shimmering placeholder blocks shown while data loads. */

export default function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`skeleton ${className}`} aria-hidden="true" />;
}

export function SkeletonText({ lines = 3, className = '' }: { lines?: number; className?: string }) {
  return (
    <div className={`space-y-2.5 ${className}`} aria-hidden="true">
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="skeleton h-4" style={{ width: `${100 - i * 12}%` }} />
      ))}
    </div>
  );
}

export function SkeletonCard({ className = '' }: { className?: string }) {
  return (
    <div className={`rounded-card bg-surface border border-edge/8 p-5 ${className}`} aria-hidden="true">
      <div className="skeleton h-3.5 w-24 mb-3" />
      <div className="skeleton h-8 w-32 mb-2" />
      <div className="skeleton h-3 w-full" />
    </div>
  );
}

export function SkeletonRows({ rows = 5, className = '' }: { rows?: number; className?: string }) {
  return (
    <div className={`space-y-2 ${className}`} aria-hidden="true">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton h-12 w-full" />
      ))}
    </div>
  );
}

export function SkeletonChart({ className = '' }: { className?: string }) {
  return (
    <div className={`rounded-card bg-surface border border-edge/8 p-5 ${className}`} aria-hidden="true">
      <div className="skeleton h-3.5 w-40 mb-4" />
      <div className="skeleton h-56 w-full" />
    </div>
  );
}
