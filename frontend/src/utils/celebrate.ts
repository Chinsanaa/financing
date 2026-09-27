/**
 * Confetti burst for genuine milestones only (e.g. a training run that
 * succeeded). canvas-confetti is loaded on demand so it never touches the
 * initial bundle, and nothing fires under prefers-reduced-motion.
 */
export async function celebrate() {
  if (typeof window === 'undefined') return;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const confetti = (await import('canvas-confetti')).default;
  const css = getComputedStyle(document.documentElement);
  const rgb = (name: string) => {
    const v = css.getPropertyValue(name).trim().split(/\s+/).map(Number);
    return v.length === 3
      ? '#' + v.map((n) => n.toString(16).padStart(2, '0')).join('')
      : '#c8ff3d';
  };
  const colors = [rgb('--accent'), rgb('--violet'), rgb('--cyan')];
  const base = { particleCount: 70, spread: 70, startVelocity: 42, ticks: 220, colors, disableForReducedMotion: true };
  confetti({ ...base, angle: 60, origin: { x: 0, y: 0.7 } });
  confetti({ ...base, angle: 120, origin: { x: 1, y: 0.7 } });
}
