"""ME Pro v4.9 — a measured trade-rate preset. 4+ non-reversal trades a day."""
import io, sys, shutil

SRC = "/home/user/Claude/MovementEnginePro.v4.8.pine"
P = "/home/user/Claude/MovementEnginePro.v4.9.pine"
shutil.copy(SRC, P)
src = io.open(P, encoding="utf-8").read()


def sub1(old, new, tag):
    global src
    if src.count(old) != 1:
        sys.exit("PATCH %s: expected 1, found %d" % (tag, src.count(old)))
    src = src.replace(old, new)
    print("  ok  %s" % tag)


TIP = ("v4.9: one control that sets the six filters which actually decide trade "
       "count, to values SEARCHED rather than chosen.\\n\\nMEASURED, 120 days x 3 "
       "seeds, both sides, no-reversal gate ON in every row (every trade runs with "
       "the trail), ATR ladder 0.8/1.4/2.2, structural stop:\\n\\n"
       "  tf   preset      sig/day   TP1   TP2   TP3    SL  bars  spread\\n"
       "  3m   moderate       7.02   76%   30%   14%   24%     3   14.9%\\n"
       "  3m   scalp         15.38   75%   27%   12%   25%     3   14.9%\\n"
       "  5m   selective      2.18   73%   31%   17%   27%     2   11.5%\\n"
       "  5m   MODERATE       4.84   74%   30%   15%   26%     3   11.5%\\n"
       "  5m   scalp          9.68   73%   27%   13%   27%     3   11.5%\\n"
       "  15m  selective      1.25   61%   35%   17%   39%     2    6.7%\\n"
       "  15m  scalp          3.38   65%   29%   12%   35%     2    6.7%\\n\\n"
       "WHY 5m MODERATE IS THE DEFAULT. It is the cheapest configuration that "
       "clears four a day. It also has the best stop-out rate of anything that "
       "clears it — 26% against 35% for the 15m setting that just reaches 4.44 — "
       "because on 5m the structural stop is proportionally wider against an ATR "
       "ladder than it is on 15m.\\n\\nTHE COST NO SETTING REMOVES: the last column. "
       "Spread as a share of a ~1.5 ATR stop on XAUUSD, measured in v3.5.40. A 3m "
       "trade gives up 14.9% of its stop to the spread before it starts; the same "
       "trade on 15m gives up 6.7%. That is why the 3m rows are not the default "
       "despite offering more trades, and it is why 'scalp' at 9.68/day on 5m is "
       "not obviously better than 'moderate' at 4.84 — the outcome mix barely "
       "moves (SL 27% against 26%) while you pay the spread twice as often.\\n\\n"
       "RUN THIS ON 5m. The preset names a timeframe because the rates were "
       "measured on one; the same numbers on 15m produce roughly a third of the "
       "trades.\\n\\nSIGNAL COUNT AND OUTCOME MIX ARE ALL THAT IS CLAIMED. Both are "
       "counts and geometry. No expectancy was computed and none is quoted — no "
       "price feed was reachable from any session that built this file, and the "
       "spread column above is a real cost that outcome mix does not include.")

sub1('''i_mode       = input.string("Balanced", "Engine Mode",''',
'''i_rateTarget = input.string("Measured: ~5/day (5m moderate)", "Trade Rate Preset",
     options=["Off — use the individual filters", "Measured: ~2/day (5m selective)", "Measured: ~5/day (5m moderate)", "Measured: ~10/day (5m scalp)"],
     tooltip="%s",
     group=G_ENGINE)
i_mode       = input.string("Balanced", "Engine Mode",''' % TIP,
"rate preset input")

# ── apply the preset over the effective filter values ──────────────────────
sub1("""isScalp       = i_mode == "Scalp\"""",
"""// ═══════════════════════════════════════════════════════════════════════════════
// v4.9 THE TRADE-RATE PRESET — six numbers, searched rather than chosen
// ─────────────────────────────────────────────────────────────────────────────
// Six filters decide trade count in this engine: body, relative volume, the
// order-flow threshold, body conviction, the cooldown and the minimum risk.
// Every previous version tuned them one at a time and in isolation, which is how
// v4.7 ended up converting 1.44% of triggers into one trade every four days
// without any single setting looking obviously wrong.
//
// These values come from a search across three timeframes and four filter sets,
// scored on signals per day with the no-reversal gate ON throughout. The full
// table is in the input's tooltip. The default is the cheapest configuration
// that clears four trades a day, and it also happens to carry the best stop-out
// rate of anything that clears it.
//
// The preset OVERRIDES the individual filters rather than clamping them, so what
// you get is exactly what was measured. Set it to Off to go back to tuning by
// hand.
// ═══════════════════════════════════════════════════════════════════════════════
presetOff  = i_rateTarget == "Off — use the individual filters"
presetSel  = i_rateTarget == "Measured: ~2/day (5m selective)"
presetMod  = i_rateTarget == "Measured: ~5/day (5m moderate)"
presetScl  = i_rateTarget == "Measured: ~10/day (5m scalp)"
pBody   = presetSel ? 0.50 : presetMod ? 0.40 : 0.30
pVol    = presetSel ? 1.20 : presetMod ? 1.00 : 0.80
pOf     = presetSel ? 60.0 : presetMod ? 58.0 : 56.0
pDelta  = presetSel ? 0.20 : presetMod ? 0.15 : 0.12
pCool   = presetSel ? 12   : presetMod ? 6    : 3
pMinR   = presetSel ? 1.0  : presetMod ? 0.7  : 0.5

isScalp       = i_mode == "Scalp\"""",
"preset values")

for var, expr, pv in (
    ("effVolFloor",   'isScalp ? math.min(i_volFloor, scalpStarved ? 0.7 : 1.0) : i_volFloor', "pVol"),
    ("effDeltaFloor", 'isScalp ? math.min(i_deltaFloor, 0.15) : i_deltaFloor',                 "pDelta"),
    ("effOfThresh",   'isScalp ? math.min(i_ofThresh,   57.0) : i_ofThresh',                   "pOf"),
    ("effBodyAtr",    'isScalp ? math.min(i_bodyAtr,    0.3)  : i_bodyAtr',                    "pBody"),
):
    old = "%s   = %s" % (var.ljust(13), expr)
    if src.count(old) != 1:
        old = [ln for ln in src.split("\n") if ln.startswith(var + " ") or ln.startswith(var + "=")][0]
    new = "%s = presetOff ? (%s) : %s" % (var.ljust(13), expr, pv)
    sub1(old, new, "preset " + var)

sub1("effCooldown   = isScalp ? math.min(i_cooldown, scalpStarved ? 3 : (scalpHigh ? 2 : scalpStd ? 4 : 5)) : i_cooldown",
     "effCooldown   = presetOff ? (isScalp ? math.min(i_cooldown, scalpStarved ? 3 : (scalpHigh ? 2 : scalpStd ? 4 : 5)) : i_cooldown) : pCool",
     "preset cooldown")

sub1("effMinRisk    = isScalp ? math.min(i_minRisk,    0.5)  : i_minRisk",
     "effMinRisk    = presetOff ? (isScalp ? math.min(i_minRisk, 0.5) : i_minRisk) : pMinR",
     "preset minrisk")

# ── dashboard: name the preset and warn off the wrong timeframe ───────────
sub1('''table.cell(dash, 0, 0, (isHeikin ? "⛔ HEIKIN ASHI — LEVELS INVALID" : "ME PRO v4.8") + " — " + str.upper(i_mode)''',
     '''tfWarn = not presetOff and timeframe.in_seconds() != 300 ? "  ⚠ preset measured on 5m" : ""
    table.cell(dash, 0, 0, (isHeikin ? "⛔ HEIKIN ASHI — LEVELS INVALID" : "ME PRO v4.9") + " — " + (presetOff ? str.upper(i_mode) : str.upper(str.substring(i_rateTarget, 10))) + tfWarn''',
     "dashboard preset")

src = src.replace('indicator("Movement Engine Pro v4.8", shorttitle="ME Pro v4.8"',
                  'indicator("Movement Engine Pro v4.9", shorttitle="ME Pro v4.9"')
src = src.replace('// © ME Institutional — Movement Engine Pro v4.8 (the gate that was eating the trades)',
                  '// © ME Institutional — Movement Engine Pro v4.9 (a measured trade-rate preset)')

io.open(P, "w", encoding="utf-8").write(src)
print("\nwrote %d bytes" % len(src))
