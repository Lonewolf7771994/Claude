"""The widened stop trades stop-outs for TIME-STOPS. How much, and does a
longer time stop recover it?

sl_diag.py measured the v2.2 hybrid stop cutting 5m stop-outs from 42% to 14%.
The cost is in the time column: 17% -> 27%. A trade that would have been
stopped now sometimes just sits. The time stop is 12 bars against a median
hold of 5, so this asks whether 12 is simply too short for the wider stop.
"""
from sl_diag import run_diag, pct
from gen import series_regime

DAYS, SEEDS = 100, (1, 2)
for tf_min in (5, 15):
    print("\n%dm — Structure + ATR targets, pad 0.25" % tf_min)
    print("  %-8s%8s%7s%7s%7s%7s%8s" % ("tstop", "trd/day", "SL", "BE", "TP3", "time", "bars"))
    for ts in (12, 20, 30, 0):
        allt = []
        for seed in SEEDS:
            m1 = series_regime(60*24*DAYS, 60, seed=seed)
            bars = []
            for j in range(0, len(m1)-tf_min+1, tf_min):
                w = m1[j:j+tf_min]
                bars.append((w[0][0], w[0][1], max(b[2] for b in w),
                             min(b[3] for b in w), w[-1][4], sum(b[5] for b in w)))
            allt += run_diag(bars, stop_mode="hybrid", struct_pad=0.25, tstop=ts)["trades"]
        n = len(allt); days = DAYS*len(SEEDS)
        med = sorted(x["dur"] for x in allt)[n//2]
        print("  %-8s%8.2f%6.0f%%%6.0f%%%6.0f%%%6.0f%%%8d" % (
            ts if ts else "off", n/days,
            pct(len([x for x in allt if x["how"]=="sl"]), n),
            pct(len([x for x in allt if x["how"]=="be"]), n),
            pct(len([x for x in allt if x["how"]=="tp3"]), n),
            pct(len([x for x in allt if x["how"]=="time"]), n), med))
