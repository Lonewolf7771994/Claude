"""THE SL BUFFER, AND THE FACT THAT TWO PADS STACK.

v2.2 builds the stop as:

    slRaw = min(invalidation, close - atr*i_minRisk) - atr*i_slBuf - atr*i_structPad

i_slBuf (0.20) and i_structPad (0.25) are SEPARATE inputs that do the SAME
job — clearance beyond the invalidation — and they add. The effective pad is
0.45 ATR, and neither input's tooltip says the other exists.

That matters beyond tidiness. A wider stop:
  - lowers position size (risk-based sizing divides by stop distance)
  - can push structural risk past i_structMax (4.0 ATR), which REJECTS the
    setup outright, so the buffer silently controls TRADE COUNT
  - does NOT move TP1, because in v2.2 targets are ATR distances and are
    deliberately decoupled from risk

So the buffer trades stop-outs against trade count, and does not touch where
TP1 sits. Measured here so the trade is visible instead of implied.
"""
from sl_diag import run_diag, pct
from gen import series_regime

DAYS, SEEDS = 100, (1, 2, 3)

for tf_min in (5, 15):
    print("\n%dm — sweeping SL buffer, struct pad held at 0.25, TP1 0.8 ATR" % tf_min)
    print("  %-12s%-10s%8s%8s%8s%8s%8s%7s" %
          ("slBuf", "total pad", "trd/day", "TP1 hit", "BE", "TP3", "SL", "bars"))
    for buf in (0.00, 0.10, 0.20, 0.35, 0.50):
        allt = []
        for seed in SEEDS:
            m1 = series_regime(60 * 24 * DAYS, 60, seed=seed)
            bars = []
            for j in range(0, len(m1) - tf_min + 1, tf_min):
                w = m1[j:j + tf_min]
                bars.append((w[0][0], w[0][1], max(b[2] for b in w),
                             min(b[3] for b in w), w[-1][4], sum(b[5] for b in w)))
            allt += run_diag(bars, stop_mode="hybrid", struct_pad=0.25, sl_buf=buf,
                             tp_r=(0.8, 1.4, 2.0), tstop=12)["trades"]
        n = len(allt)
        if not n:
            continue
        days = DAYS * len(SEEDS)
        be  = sum(1 for x in allt if x["how"] == "be")
        tp3 = sum(1 for x in allt if x["how"] == "tp3")
        sl  = sum(1 for x in allt if x["how"] == "sl")
        print("  %-12.2f%-10.2f%8.2f%7.0f%%%7.0f%%%7.0f%%%7.0f%%%7d" % (
            buf, buf + 0.25, n / days, pct(be + tp3, n), pct(be, n),
            pct(tp3, n), pct(sl, n), sorted(x["dur"] for x in allt)[n // 2]))
print("\n  total pad = slBuf + structPad, the clearance actually applied.")
print("  Counts and geometry only, synthetic data, no expectancy.")
