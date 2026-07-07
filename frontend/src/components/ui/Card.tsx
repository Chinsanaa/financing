import { HTMLAttributes, ReactNode } from 'react';

export default function Card({
  glass = false,
  hover = false,
  children,
  className = '',
  ...rest
}: HTMLAttributes<HTMLDivElement> & {
  glass?: boolean;
  hover?: boolean;
  children: ReactNode;
}) {
  return (
    <div
      className={`rounded-card ${
        glass ? 'glass' : 'bg-surface border border-edge/8'
      } ${
        hover
          ? 'transition-all duration-200 hover:-translate-y-0.5 hover:border-accent/30 hover:shadow-glow'
          : ''
      } ${className}`}
      {...rest}
    >
      {children}
    </div>
  );
}

export function SectionHeader({
  label,
  title,
  action,
}: {
  label?: string;
  title: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex items-end justify-between gap-4 mb-4">
      <div>
        {label && <p className="section-label mb-1">{label}</p>}
        <h2 className="font-display text-xl font-semibold tracking-tight">{title}</h2>
      </div>
      {action}
    </div>
  );
}
