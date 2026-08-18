# ME Pro measurement harness

A Python port of the indicator's signal path, built because 37 versions shipped
without the logic ever being executed. Every change before this was reasoned,
not measured — including several that were wrong.

## What it answers

Run `python3 report.py`. It executes the real trigger construction, every gate,
the TP ladder (with the v3.5.21 spacing and v3.5.35 ceiling) and a bar-by-bar
outcome walk over synthetic OHLCV shaped like intraday gold.

## What it found

**1. Signal rate scales correctly with timeframe.** Lower timeframes fire more,
which settles the "30m signals while 5m and 15m are silent" question — that was
a quiet day, not a mechanism.

    tf    triggers/day   signals/day (Scalp/Selective)
    5m      142.3          4.34
    15m      46.3          1.36
    30m      23.0          0.67
    1H       11.1          0.29
    4H        3.0          0.12

**2. The plan has no structural money leak.** On driftless data a sound plan
must score ~0.00R. Across 8 seeds:

    tf    trades   mean R    t-stat
    5m     3350    -0.039    -2.06
    15m    1089    -0.042    -1.26
    30m     509    +0.006    +0.13
    1H      255    +0.043    +0.59

A single seed showed 5m at -0.135R and looked like a defect. It was sampling
noise. Eight seeds put every timeframe at fair-game neutral.

**3. Trade count above 15m is bounded by trigger supply, not by gates.**
Targets of 2/day on 30m, 1/day on 1H and 0.5/day on 4H are unreachable even
with the reward gate at 0, the cooldown at 2 and the volume floor at 0.8. There
are only 23 / 11 / 3 triggers per day to work with. More trades on those charts
requires redefining what counts as a structure event — not tuning.

On 15m, 3 signals/day IS reachable, but only with the reward gate fully
disabled (min_rr 0) and the volume floor at 0.8.

## What it CANNOT answer

Driftless synthetic data is a fair game by construction, so **every setting
scores EV ~0**. The harness measures COUNT, SPACING and STRUCTURAL SOUNDNESS.
It cannot tell you whether looser gates trade worse, or whether the engine has
an edge on real gold. Only real price can.

## Known deviations from the Pine

- FRVP/POC/VAH/VAL are not ported, so VAH/VAL never appear as TP candidates.
  Structure targets are therefore under-represented and the ladder falls back to
  R-multiples more often here than on a live chart.
- VWAP and its overextension guard are not ported.
- Session and news filters are not ported (both default off).
- Intrabar order between stop and target is resolved conservatively: on a bar
  touching both, the stop wins for TP1.
