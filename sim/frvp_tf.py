"""Verify the time-anchored FRVP window: does POC/VAH/VAL agree across timeframes?

ONE 1-minute price path is resampled to 5m/15m/30m/1H. Every chart therefore
sees the identical market. Any disagreement in POC/VAH/VAL is a defect in the
profile, not a property of the data.

This measures GEOMETRY ONLY (where the levels land). It says nothing about
expectancy and must not be read as saying anything about it.
"""
import sys
from gen import series_regime
from engine import frvp

TFS = [("5m", 5), ("15m", 15), ("30m", 30), ("1H", 60)]
MAXBARS = 600          # i_frvpMaxBars default
BINS = 32              # i_frvpBins default


def resample(m1, k):
    out = []
    for i in range(0, len(m1) - k + 1, k):
        w = m1[i:i + k]
        out.append((w[0][0], w[0][1], max(b[2] for b in w), min(b[3] for b in w),
                    w[-1][4], sum(b[5] for b in w)))
    return out


def spread(xs):
    xs = [x for x in xs if x is not None]
    return max(xs) - min(xs) if len(xs) > 1 else 0.0


def report(title, len_for):
    rows = []
    for name, k in TFS:
        b = resample(m1, k)
        L = len_for(k)
        p, vh, vl = frvp(b, length=L, bins=BINS, stride=1)
        rows.append((name, L, L * k / 60.0, p[-1], vh[-1], vl[-1]))
    print(f"\n{title}")
    print(f"  {'tf':<5}{'bars':>6}{'hours':>8}{'POC':>12}{'VAH':>12}{'VAL':>12}")
    for name, L, hrs, p, vh, vl in rows:
        print(f"  {name:<5}{L:>6}{hrs:>8.1f}{p:>12.2f}{vh:>12.2f}{vl:>12.2f}")
    print(f"  spread across the four charts:  "
          f"POC {spread([r[3] for r in rows]):.2f}   "
          f"VAH {spread([r[4] for r in rows]):.2f}   "
          f"VAL {spread([r[5] for r in rows]):.2f}")


m1 = series_regime(60 * 24 * 40, 60, seed=11)

report("BARS (legacy anchor): i_frvpLen = 100",
       lambda k: 100)

for hours in (24.0, 72.0):
    report(f"HOURS anchor: i_frvpHours = {hours:g}, cap {MAXBARS} bars",
           lambda k, h=hours: max(20, min(MAXBARS, round(h * 60 / k))))

# what the cap actually costs on the lowest timeframes
print("\nclamp behaviour at 24h (cap 600 bars) — what the dashboard must show:")
for name, k in [("1m", 1), ("2m", 2), ("3m", 3), ("5m", 5), ("15m", 15)]:
    want = round(24.0 * 60 / k)
    eff = max(20, min(MAXBARS, want))
    print(f"  {name:<4} wants {want:>4} bars -> uses {eff:>4}  "
          f"= {eff * k / 60.0:>5.1f}h  {'~ CLAMPED (shown in red)' if eff < want else ''}")
