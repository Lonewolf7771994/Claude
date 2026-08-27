"""TP1 BARELY HITS. How far away is it, and what does moving it do?

Reported from the chart: on 5m and 15m the v2.2 plan rarely reaches TP1.

v2.2's design intent was the opposite. The stop moved out to structure
(roughly 2 ATR) while TP1 stayed at 0.8 ATR, which makes TP1 about 0.35R —
deliberately close, so it is reached often and arms breakeven. If it is not
being reached, either the distance is wrong for real gold or the design
assumption is.

This sweeps TP1 distance and reports how often it is actually touched, plus
what that does to the rest of the outcome mix. TP1 is the only target that
matters structurally: reaching it is what moves the stop to breakeven, so a
TP1 that does not fill means the trade carries full risk the whole way.
"""
from sl_diag import run_diag, pct
from gen import series_regime

DAYS, SEEDS = 100, (1, 2, 3)

for tf_min in (5, 15):
    print("\n%dm — v2.2 default stop (structure + 0.25 pad), targets in ATR" % tf_min)
    print("  %-10s%8s%8s%8s%8s%8s%7s" %
          ("TP1", "trades", "TP1 hit", "BE", "TP3", "SL", "bars"))
    for tp1 in (0.4, 0.5, 0.6, 0.8, 1.0):
        allt = []
        for seed in SEEDS:
            m1 = series_regime(60 * 24 * DAYS, 60, seed=seed)
            bars = []
            for j in range(0, len(m1) - tf_min + 1, tf_min):
                w = m1[j:j + tf_min]
                bars.append((w[0][0], w[0][1], max(b[2] for b in w),
                             min(b[3] for b in w), w[-1][4], sum(b[5] for b in w)))
            allt += run_diag(bars, stop_mode="hybrid", struct_pad=0.25,
                             tp_r=(tp1, 1.4, 2.0), tstop=12)["trades"]
        n = len(allt)
        if not n:
            continue
        # a trade reached TP1 if it ended at BE, at TP3, or timed out having
        # armed BE — the harness records the exit type, so BE + TP3 is the
        # floor on TP1 reach and is what is reported here.
        be  = sum(1 for x in allt if x["how"] == "be")
        tp3 = sum(1 for x in allt if x["how"] == "tp3")
        sl  = sum(1 for x in allt if x["how"] == "sl")
        print("  %-10.2f%8d%7.0f%%%7.0f%%%7.0f%%%7.0f%%%7d" % (
            tp1, n, pct(be + tp3, n), pct(be, n), pct(tp3, n), pct(sl, n),
            sorted(x["dur"] for x in allt)[n // 2]))
print("\n  TP1 hit is the floor: BE + TP3, i.e. trades that demonstrably")
print("  reached it. Counts and geometry only, synthetic data, no expectancy.")
