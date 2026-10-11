/**
 * Alipay mark — inline SVG, no runtime fetching.
 *
 * Source (downloaded 2026-10-11):
 *   https://cdn.jsdelivr.net/npm/simple-icons@13.21.0/icons/alipay.svg
 *   Simple Icons' vector of the official Alipay app mark, sourced from Alipay's
 *   brand guidelines: https://global.alipay.com/docs/ac/website_hk/design
 *   Brand color #1677FF (same source).
 * The current Wikipedia file (en.wikipedia "Alipay_logo_(2024).svg") uses
 * color ramps and an embedded bitmap, so per THE RULE (solid colors) we use the
 * official flat single-color mark instead. The path is unmodified.
 *
 * The mark contains the Chinese character "zhi" (U+652F) as part of the artwork. This is the one
 * user-approved exception to "no Chinese in the UI": it is rendered as an
 * image (role="img", aria-label "Alipay"), never as text. Always print the
 * word "Alipay" next to it (see FormatBadges) — the logo is never the only label.
 * Not affiliated with Ant Group; Alipay is a trademark of its owner.
 */
const ALIPAY_PATH =
  'M19.695 15.07c3.426 1.158 4.203 1.22 4.203 1.22V3.846c0-2.124-1.705-3.845-3.81-3.845H3.914C1.808.001.102 1.722.102 3.846v16.31c0 2.123 1.706 3.845 3.813 3.845h16.173c2.105 0 3.81-1.722 3.81-3.845v-.157s-6.19-2.602-9.315-4.119c-2.096 2.602-4.8 4.181-7.607 4.181-4.75 0-6.361-4.19-4.112-6.949.49-.602 1.324-1.175 2.617-1.497 2.025-.502 5.247.313 8.266 1.317a16.796 16.796 0 0 0 1.341-3.302H5.781v-.952h4.799V6.975H4.77v-.953h5.81V3.591s0-.409.411-.409h2.347v2.84h5.744v.951h-5.744v1.704h4.69a19.453 19.453 0 0 1-1.986 5.06c1.424.52 2.702 1.011 3.654 1.333m-13.81-2.032c-.596.06-1.71.325-2.321.869-1.83 1.608-.735 4.55 2.968 4.55 2.151 0 4.301-1.388 5.99-3.61-2.403-1.182-4.438-2.028-6.637-1.809';

export const ALIPAY_BLUE = '#1677FF';

export default function AlipayLogo({
  size = 16,
  variant = 'color',
  className = '',
  decorative = false,
}: {
  /** Height (and width — the mark is square) in px. */
  size?: number;
  /** `color` = official Alipay blue; `mono` = currentColor. */
  variant?: 'color' | 'mono';
  className?: string;
  /** True when a visible "Alipay" label sits right next to the mark. */
  decorative?: boolean;
}) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      className={`shrink-0 ${className}`}
      {...(decorative ? { 'aria-hidden': true } : { role: 'img', 'aria-label': 'Alipay' })}
    >
      <path d={ALIPAY_PATH} fill={variant === 'mono' ? 'currentColor' : ALIPAY_BLUE} />
    </svg>
  );
}
