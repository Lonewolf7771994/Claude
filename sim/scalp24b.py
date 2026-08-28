"""ME SCALP v2.4 — round two. Where the stop-outs actually are, per family.

Round one settled the entry-zone question: the VWAP band trigger fires on
ARITHMETIC, not on a rejection. At session open the deviation is computed from
one sample, so u1 == l1 == vwap and "low <= l1 and close > l1" is trivially
true. Those events resolve into the time stop and nowhere else — 5m band TP1
30% against 61% for MSS, 15m band TP1 25% with a 52% time-stop share and a
median hold sitting exactly on the 12-bar time stop.

Requiring the band to have WIDTH removes them almost for free.

This file asks the remaining question: the 15m stop-out rate is still 28%, and
round one showed MSS at 36% on 15m — the worst family in the engine. MSS builds
its stop from the PREVIOUS PIVOT, which on 15m can sit a few ticks from the
entry. So the pad that is right for a fade may be wrong for a break.

Counts and outcome geometry only. NO EXPECTANCY COMPUTED OR QUOTED.
"""
from scalp24 import run, row, pct, HDR, DAYS, SEEDS, FADE

CONF = ("band", "band2", "value")      # the families that must be confirmed
BW = 0.30                               # band width floor, in ATR

days = DAYS * len(SEEDS)

for tf in (5, 15):
    print("\n" + "=" * 96)
    print("%dm — recommended base: band width %.2f ATR, fades confirmed" % (tf, BW))
    print("=" * 96)
    print(HDR)
    base, _, _ = run(tf)
    row("v2.3 as shipped", base, days)
    rec, _, _ = run(tf, band_w=BW, confirm_only=CONF)
    row("v2.4 candidate", rec, days)

    print("\n  v2.4 candidate, by family:")
    for nm in ("mss", "fvg", "sweep", "band", "band2", "value"):
        row("  " + nm, [x for x in rec if x["name"] == nm], days)

    print("\n  stop pad, swept further (total = slBuf 0.20 + structPad):")
    for sp in (0.25, 0.40, 0.55, 0.70, 0.85):
        t, _, _ = run(tf, band_w=BW, confirm_only=CONF, struct_pad=sp)
        row("  total %.2f ATR" % (0.20 + sp), t, days,
            "   median risk %.2f ATR" % sorted(x["r"] for x in t)[len(t) // 2])

    print("\n  pad for MSS only, everything else held at 0.45 total:")
    for mp in (0.25, 0.45, 0.65, 0.85):
        t, _, _ = run(tf, band_w=BW, confirm_only=CONF, pad_by={"mss": mp})
        sub = [x for x in t if x["name"] == "mss"]
        row("  mss pad %.2f total" % (0.20 + mp), t, days,
            "   mss SL %.0f%%  n=%d" % (pct(sum(1 for x in sub if x["how"] == "sl"),
                                            len(sub)), len(sub)))

    print("\n  time stop, under the v2.4 candidate:")
    for ts in (8, 12, 18, 24):
        t, _, _ = run(tf, band_w=BW, confirm_only=CONF, tstop=ts)
        row("  %d bars" % ts, t, days)

print("\n  Counts and outcome geometry only. NO EXPECTANCY COMPUTED OR QUOTED.")
