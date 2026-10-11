import FormatBadges from '@/components/brand/FormatBadges';

/**
 * "Works with exports from" — the one place on the landing body where the
 * Alipay / WeChat Pay marks appear (DESIGN_SYSTEM §5: small, next to
 * accepted-formats text, label always visible). The trademark line lives in
 * the shared SiteFooter.
 */
export default function FormatsStrip() {
  return (
    <div className="flex flex-col gap-2.5 border-y border-edge/15 py-4 sm:flex-row sm:items-center sm:gap-6">
      <p className="text-[13px] text-muted">Works with exports from</p>
      <FormatBadges size={18} />
    </div>
  );
}
