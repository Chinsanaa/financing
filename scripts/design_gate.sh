#!/usr/bin/env bash
# Design gate — enforces THE RULE (docs/DESIGN_SYSTEM.md): solid colors only,
# no gradients / glows / blur / glass, no purple.
#
#   bash scripts/design_gate.sh          # from the repo root (or anywhere)
#
# 1. Greps frontend/src for forbidden patterns (case-insensitive), incl. a
#    bare Tailwind `blur` class. Allowlist: a line containing
#    `design-gate: allow` is skipped — use it only for comments that explain
#    the rule.
# 2. Parses every color literal in every *.ts / *.tsx / *.css under
#    frontend/src — #rrggbb / #rrggbbaa hexes, `R G B` channel tokens,
#    hsl()/hsla() and oklch() — and fails on OKLCH hue 270-335 deg with
#    chroma > 0.04 (purple / violet / magenta).
# Exit 0 = clean, 1 = hits (listed).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/frontend/src"
PATTERN='gradient|backdrop-blur|blur-|blur\(|glass|violet|indigo|fuchsia|purple|plum|shadow-glow|drop-shadow'
# Bare Tailwind `blur` class: checked on code lines only (comment lines that
# start with *, //, /* or {/* may say "no blur" in prose).
BARE='\bblur\b'
INCLUDES=(--include='*.ts' --include='*.tsx' --include='*.js' --include='*.jsx' --include='*.css' --include='*.mdx')
fail=0

echo "design-gate: scanning frontend/src for forbidden patterns"
hits="$( {
  grep -rnEi "$PATTERN" "$SRC" "${INCLUDES[@]}" || true
  grep -rnEi "$BARE" "$SRC" "${INCLUDES[@]}" | grep -vE '^[^:]+:[0-9]+:[[:space:]]*(\*|//|/\*|\{/\*)' || true
} | grep -v 'design-gate: allow' | sort -u || true)"
if [ -n "$hits" ]; then
  echo "FAIL: forbidden pattern(s):"
  echo "$hits" | sed "s|^$ROOT/|  |"
  fail=1
else
  echo "  ok: no forbidden patterns"
fi

echo "design-gate: checking color hues in frontend/src (OKLCH 270-335 deg, C > 0.04 is forbidden)"
PY="$(command -v python3 || command -v python || true)"
if [ -z "$PY" ]; then
  echo "FAIL: python3 not found (needed for the hue check)"
  exit 1
fi
if ! "$PY" - "$SRC" <<'PYEOF'
import math, os, re, sys

def s2l(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def oklch_from_rgb(r, g, b):
    r, g, b = (s2l(max(0.0, min(1.0, v / 255))) for v in (r, g, b))
    l = 0.4122214708*r + 0.5363325363*g + 0.0514459929*b
    m = 0.2119034982*r + 0.6806995451*g + 0.1073969566*b
    s = 0.0883024619*r + 0.2817188376*g + 0.6299787005*b
    l, m, s = (math.copysign(abs(v) ** (1/3), v) for v in (l, m, s))
    L = 0.2104542553*l + 0.7936177850*m - 0.0040720468*s
    a = 1.9779984951*l - 2.4285922050*m + 0.4505937099*s
    bb = 0.0259040371*l + 0.7827717662*m - 0.8086757660*s
    return L, math.hypot(a, bb), math.degrees(math.atan2(bb, a)) % 360

def hsl_to_rgb(h, s, l):
    h = (h % 360) / 360
    def f(n):
        k = (n + h * 12) % 12
        return l - s * min(l, 1 - l) * max(-1, min(k - 3, 9 - k, 1))
    return f(0) * 255, f(8) * 255, f(4) * 255

def angle(v, unit):
    v = float(v)
    return {'rad': math.degrees(v), 'turn': v * 360, 'grad': v * 0.9}.get(unit, v)

NUM = r'(-?[\d.]+)'
HEX = re.compile(r'#([0-9a-fA-F]{6})(?:[0-9a-fA-F]{2})?\b')
TRIP = re.compile(r'(?<![\d.#])(\d{1,3}) (\d{1,3}) (\d{1,3})(?=\s*(?:;|/|\)))')
HSL = re.compile(r'hsla?\(\s*' + NUM + r'(deg|rad|turn|grad)?[\s,]+' + NUM + r'%[\s,]+' + NUM + r'%', re.I)
OKLCH = re.compile(r'oklch\(\s*' + NUM + r'(%?)\s+' + NUM + r'(%?)\s+' + NUM + r'(deg|rad|turn|grad)?', re.I)

bad, n = [], 0
for dirpath, _, files in os.walk(sys.argv[1]):
    for fn in files:
        if not fn.endswith(('.ts', '.tsx', '.css')):
            continue
        path = os.path.join(dirpath, fn)
        for no, line in enumerate(open(path, encoding='utf-8', errors='replace'), 1):
            if 'design-gate: allow' in line:
                continue
            found = []  # (text, L, C, H)
            for mt in HEX.finditer(line):
                hx = mt.group(1)
                found.append((mt.group(0), *oklch_from_rgb(*(int(hx[i:i+2], 16) for i in (0, 2, 4)))))
            for mt in TRIP.finditer(line):
                v = [int(x) for x in mt.groups()]
                if all(x <= 255 for x in v):
                    found.append((mt.group(0), *oklch_from_rgb(*v)))
            for mt in HSL.finditer(line):
                h, unit, s, l = mt.groups()
                found.append((mt.group(0) + ')', *oklch_from_rgb(*hsl_to_rgb(angle(h, unit), float(s) / 100, float(l) / 100))))
            for mt in OKLCH.finditer(line):
                L, lp, C, cp, H, unit = mt.groups()
                L = float(L) / 100 if lp else float(L)
                C = float(C) / 100 * 0.4 if cp else float(C)
                found.append((mt.group(0) + ')', L, C, angle(H, unit) % 360))
            for text, L, C, H in found:
                n += 1
                if C > 0.04 and 270 <= H <= 335:
                    rel = os.path.relpath(path, os.path.dirname(os.path.dirname(sys.argv[1])))
                    bad.append(f"  {rel}:{no}: {text} (OKLCH L={L:.2f} C={C:.3f} H={H:.0f})")
if bad:
    print("FAIL: purple-range colors:")
    print("\n".join(bad))
    sys.exit(1)
print(f"  ok: {n} color literals checked, none in the purple range")
PYEOF
then
  fail=1
fi

if [ "$fail" -ne 0 ]; then
  echo "design-gate: FAILED"
  exit 1
fi
echo "design-gate: PASSED"
