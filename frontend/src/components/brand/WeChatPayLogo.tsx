/**
 * WeChat Pay mark — inline SVG, no runtime fetching.
 *
 * Source (downloaded 2026-10-11): the official WeChat Pay site header logo,
 *   https://pay.weixin.qq.com/ → https://td.cdn-go.cn/enterprise_payment/v0.1.2/logo.svg
 * Only the symbol path (the green speech bubble with the check, fill #22AC38)
 * is used, unmodified. The file's Chinese wordmark is left out because the UI
 * must not render Chinese text; the English label "WeChat Pay" is printed next
 * to the mark instead (see FormatBadges).
 *
 * Contrast note: #22AC38 is 5.6:1 on the dark surface but 2.75:1 on the light
 * surface. Logos are exempt from WCAG 1.4.11 and the mark is always paired
 * with its text label, so the official color is kept in both themes; use
 * `variant="mono"` (currentColor) where a single-ink look is wanted.
 * Not affiliated with Tencent; WeChat Pay is a trademark of its owner.
 */
const WECHAT_PAY_PATH =
  'M13.9879326,21.4155844 C13.8125353,21.5038961 13.637138,21.5480519 13.4178914,21.5480519 C12.9355489,21.5480519 12.5409051,21.2831169 12.3216585,20.8857143 L12.2339598,20.7090909 L8.76986368,13.1142857 C8.72601436,13.025974 8.72601436,12.9376623 8.72601436,12.8493506 C8.72601436,12.4961039 8.98911027,12.2311688 9.33990482,12.2311688 C9.47145277,12.2311688 9.60300073,12.2753247 9.73454868,12.3636364 L13.8125353,15.2779221 C14.1194805,15.4545455 14.4702751,15.587013 14.8649189,15.587013 C15.0841655,15.587013 15.3034121,15.5428571 15.5226587,15.4545455 L34.6409615,6.88831169 C31.2207147,2.82597403 25.5641526,0.176623377 19.1621521,0.176623377 C8.72601436,0.176623377 0.219246592,7.28571429 0.219246592,16.0727273 C0.219246592,20.8415584 2.76250706,25.1688312 6.75279503,28.0831169 C7.05974026,28.3038961 7.27898685,28.7012987 7.27898685,29.0987013 C7.27898685,29.2311688 7.23513753,29.3636364 7.19128821,29.4961039 C6.88434299,30.6883117 6.35815117,32.6311688 6.35815117,32.7194805 C6.31430185,32.8519481 6.27045253,33.0285714 6.27045253,33.2051948 C6.27045253,33.5584416 6.53354844,33.8233766 6.88434299,33.8233766 C7.01589094,33.8233766 7.1474389,33.7792208 7.23513753,33.6909091 L11.3569735,31.2623377 C11.6639187,31.0857143 12.0147132,30.9532468 12.3655078,30.9532468 C12.5409051,30.9532468 12.7601516,30.9974026 12.9355489,31.0415584 C14.8649189,31.6155844 16.9696862,31.9246753 19.1183028,31.9246753 C29.5544406,31.9246753 38.0612084,24.8155844 38.0612084,16.0285714 C38.0612084,13.3792208 37.2719206,10.8623377 35.9125918,8.65454545 L14.1194805,21.3272727 L13.9879326,21.4155844 Z';

export const WECHAT_PAY_GREEN = '#22AC38';

// Symbol bounds in the source file: x 0.22–38.06, y 0.18–33.82.
const VB_W = 38.3;
const VB_H = 34;

export default function WeChatPayLogo({
  size = 16,
  variant = 'color',
  className = '',
  decorative = false,
}: {
  /** Height in px (width follows the mark's aspect ratio). */
  size?: number;
  /** `color` = official WeChat Pay green; `mono` = currentColor. */
  variant?: 'color' | 'mono';
  className?: string;
  /** True when a visible "WeChat Pay" label sits right next to the mark. */
  decorative?: boolean;
}) {
  return (
    <svg
      viewBox={`0 0 ${VB_W} ${VB_H}`}
      height={size}
      width={Math.round((size * VB_W) / VB_H * 100) / 100}
      className={`shrink-0 ${className}`}
      {...(decorative ? { 'aria-hidden': true } : { role: 'img', 'aria-label': 'WeChat Pay' })}
    >
      <path d={WECHAT_PAY_PATH} fill={variant === 'mono' ? 'currentColor' : WECHAT_PAY_GREEN} />
    </svg>
  );
}
