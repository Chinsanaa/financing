#!/usr/bin/env bash
# Design gate — enforces THE RULE (docs/DESIGN_SYSTEM.md): solid colors only,
# no gradients / glows / blur / glass, no purple.
#
#   bash scripts/design_gate.sh          # from the repo root (or anywhere)
#
# 1. Greps frontend/src for forbidden patterns (case-insensitive).
#    Allowlist: a line containing `design-gate: allow` is skipped — use it
#    only for comments that explain the rule or for a legacy name that is
#    proven solid (e.g. the `.glass` class, which is a flat surface).
# 2. Parses every color in globals.css and categoryColors.ts (#rrggbb hexes
#    and `R G B` channel tokens) and fails on OKLCH hue 270-335 deg with
#    chroma > 0.04 (purple / violet / magenta).
# Exit 0 = clean, 1 = hits (listed).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/frontend/src"
PATTERN='gradient|backdrop-blur|blur-|blur\(|glass|violet|indigo|fuchsia|purple|plum|shadow-glow|drop-shadow'
fail=0

echo "design-gate: scanning frontend/src for forbidden patterns"
hits="$(grep -rnEi "$PATTERN" "$SRC" --include='*.ts' --include='*.tsx' --include='*.js' --include='*.jsx' --include='*.css' --include='*.mdx' \
  | grep -v 'design-gate: allow' || true)"
if [ -n "$hits" ]; then
  echo "FAIL: forbidden pattern(s):"
  echo "$hits" | sed "s|^$ROOT/|  |"
  fail=1
else
  echo "  ok: no forbidden patterns"
fi

echo "design-gate: checking palette hues (OKLCH 270-335 deg, C > 0.04 is forbidden)"
PY="$(command -v python3 || command -v python || true)"
if [ -z "$PY" ]; then
  echo "FAIL: python3 not found (needed for the hue check)"
  exit 1
fi
if ! "$PY" - "$SRC/app/globals.css" "$SRC/utils/categoryColors.ts" <<'PYEOF'
import math, re, sys

def s2l(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def oklch(r, g, b):
    r, g, b = (s2l(v / 255) for v in (r, g, b))
    l = 0.4122214708*r + 0.5363325363*g + 0.0514459929*b
    m = 0.2119034982*r + 0.6806995451*g + 0.1073969566*b
    s = 0.0883024619*r + 0.2817188376*g + 0.6299787005*b
    l, m, s = (math.copysign(abs(v) ** (1/3), v) for v in (l, m, s))
    L = 0.2104542553*l + 0.7936177850*m - 0.0040720468*s
    a = 1.9779984951*l - 2.4285922050*m + 0.4505937099*s
    bb = 0.0259040371*l + 0.7827717662*m - 0.8086757660*s
    return L, math.hypot(a, bb), math.degrees(math.atan2(bb, a)) % 360

bad, n = [], 0
for path in sys.argv[1:]:
    for no, line in enumerate(open(path, encoding='utf-8'), 1):
        cols = [(m.group(0), tuple(int(m.group(1)[i:i+2], 16) for i in (0, 2, 4)))
                for m in re.finditer(r'#([0-9a-fA-F]{6})\b', line)]
        cols += [(m.group(0).strip(), tuple(int(x) for x in m.groups()))
                 for m in re.finditer(r'(?<![\d.])(\d{1,3}) (\d{1,3}) (\d{1,3})(?=\s*(?:;|/|\)))', line)
                 if all(int(x) <= 255 for x in m.groups())]
        for text, rgb in cols:
            n += 1
            L, C, H = oklch(*rgb)
            if C > 0.04 and 270 <= H <= 335:
                bad.append(f"  {path.split('/frontend/')[-1]}:{no}: {text} (OKLCH L={L:.2f} C={C:.3f} H={H:.0f})")
if bad:
    print("FAIL: purple-range colors:")
    print("\n".join(bad))
    sys.exit(1)
print(f"  ok: {n} colors checked, none in the purple range")
PYEOF
then
  fail=1
fi

if [ "$fail" -ne 0 ]; then
  echo "design-gate: FAILED"
  exit 1
fi
echo "design-gate: PASSED"
