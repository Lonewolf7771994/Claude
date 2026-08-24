"""ME Pro v4.6 — the Prism trail: adaptive stepped trend band, rank-driven."""
import io, sys, shutil

SRC = "/home/user/Claude/MovementEnginePro.v4.5.pine"
P = "/home/user/Claude/MovementEnginePro.v4.6.pine"
shutil.copy(SRC, P)
src = io.open(P, encoding="utf-8").read()


def sub1(old, new, tag):
    global src
    if src.count(old) != 1:
        sys.exit("PATCH %s: expected 1, found %d" % (tag, src.count(old)))
    src = src.replace(old, new)
    print("  ok  %s" % tag)


# ── INPUT GROUP ────────────────────────────────────────────────────────────
sub1('var string G_VIS    = "══ Visuals ══"',
     'var string G_PRISM  = "══ Trend Trail ══"\nvar string G_VIS    = "══ Visuals ══"',
     "prism group")

sub1('i_buyCol     = input.color(color.new(#00E5FF, 0),  "BUY Color",  group=G_VIS)',
"""i_prismOn    = input.bool(true, "Show Trend Trail",
     tooltip="v4.6: a stepped volatility trail that only ever moves in the direction of the trend, plotted continuously and shaded down to price.\\n\\nThis engine has always had a dozen ways to READ direction — an HTF EMA, an 8/21 stack, a CVD cross, the leg, the efficiency ratio — and no single line on the chart that SHOWED one. The trail is that line. Price closing through it is what defines the trend state, its age, and the level the trend is currently defended at.\\n\\nIt is the same construction the v4.5 stop trail uses (ratchet in one direction, never loosen), promoted from a per-trade device to a permanent read of the chart.",
     group=G_PRISM)
i_prismAtrLen = input.int(12, "Trail ATR Length", minval=2, maxval=100, group=G_PRISM)
i_prismBase  = input.float(3.0, "Base Multiplier (× ATR)", minval=0.5, maxval=10.0, step=0.1,
     tooltip="v4.6: how many ATRs the trail sits away from the running extreme before the volatility adjustment below is applied. Wider trails flip less often and give back more of a move; tighter ones flip on ordinary pullbacks.",
     group=G_PRISM)
i_prismRefr  = input.float(0.35, "Volatility Refinement", minval=0.0, maxval=1.5, step=0.05,
     tooltip="v4.6: how much the live multiplier is allowed to tighten when volatility is historically LOW.\\n\\n    live multiplier = base − refinement × (1 − volatility rank)\\n\\nThe rank is where the current ATR sits against its own last N bars, 0 to 1. When volatility is at the bottom of its range the ATR is already small, so a full base multiple over-widens the trail and the trend state stops reacting to anything; when volatility is high the full base is what keeps you from being shaken out. So the trail tightens in quiet markets and holds its width in fast ones.\\n\\nAt 0 the multiplier is a constant and the trail is an ordinary fixed-multiple stop. The dashboard prints the live value every bar.",
     group=G_PRISM)
i_prismRank  = input.int(200, "Volatility Rank Window (bars)", minval=20, maxval=1000,
     tooltip="v4.6: how much history the current ATR is ranked against. Longer is a more stable notion of what 'normal volatility' means for this instrument and slower to re-learn after a regime change.",
     group=G_PRISM)
i_prismFill  = input.bool(true, "Shade Trail To Price", group=G_PRISM)
i_prismUpCol = input.color(#26A69A, "Trail Up Color",   group=G_PRISM)
i_prismDnCol = input.color(#EF5350, "Trail Down Color", group=G_PRISM)
i_prismGate  = input.bool(true, "Use Trail As The Trend In The No-Reversal Gate",
     tooltip="v4.6: replaces `close vs close[legLen]` with the trail's own trend state as the LEG half of the no-reversal gate.\\n\\nThe leg test asks whether price is higher than it was a fixed number of bars ago, which answers a question nobody asks: it flips on any bar where the comparison bar happens to be higher, regardless of whether structure changed. The trail flips only when price CLOSES THROUGH a level that has been ratcheting in one direction — a state with a defined level behind it and an age you can read.\\n\\nThe other halves of the gate (efficiency ratio, HTF) are untouched, and the leakage audit still holds by construction: a long requires the trail to be in its up state, so a long against the trail cannot pass.\\n\\nOff restores the v4.4 leg test exactly.",
     group=G_PRISM)
i_prismGrade = input.bool(true, "Grade Signals On The Label",
     tooltip="v4.6: prints the signal's grade and the conditions behind it on the arrow — BUY G3/3, and beneath it the volatility regime and the live multiplier the trail was running at.\\n\\nThe three graded checks are momentum, participation and candle quality. They are read off values the engine already computes, so this adds no new logic — it makes the reason a signal was taken legible at the point where you are looking, instead of only in the dashboard on the last bar.",
     group=G_PRISM)
i_buyCol     = input.color(color.new(#00E5FF, 0),  "BUY Color",  group=G_VIS)""",
"prism inputs")

# ── THE TRAIL ENGINE, right after the ATR block ────────────────────────────
sub1("""atrBase   = math.max(atr14, atr50)""",
"""atrBase   = math.max(atr14, atr50)

// ═══════════════════════════════════════════════════════════════════════════════
// v4.6 THE TREND TRAIL — one line that states the trend, its level and its age
// ─────────────────────────────────────────────────────────────────────────────
// This engine has always had many ways to READ direction and no single object on
// the chart that SHOWED one. It had an HTF EMA bias, an 8/21 momentum stack, a
// CVD cross, a leg test and an efficiency ratio — five opinions, none of them a
// level, none of them with an age, and none of them something price can be said
// to have BROKEN.
//
// The trail is that object. It is the same construction the v4.5 stop trail uses
// — ratchet in one direction, never loosen — promoted from a per-trade device to
// a permanent read of the chart. Price closing through it is what flips the
// trend state, which means the state always has a defended level behind it and a
// countable age.
//
// THE LIVE MULTIPLIER. A fixed multiple of ATR is wrong at both ends of the
// volatility distribution: when ATR is historically small the trail sits so far
// out that the state stops reacting to anything, and when ATR is large a tight
// multiple is shaken out by ordinary noise. So the multiple is a function of
// where the current ATR sits against its own history:
//
//     live = base − refinement × (1 − rank)
//
// rank is the percentile of the current ATR within the last i_prismRank bars.
// At the top of the range the full base applies; at the bottom the trail
// tightens by the refinement. The dashboard prints the live value every bar so
// the number governing the trail is never hidden.
//
// NON-REPAINTING. The state advances on confirmed bars only and each new stop is
// a function of the previous stop and the closed bar, so a level once set cannot
// be revised by later data.
// ═══════════════════════════════════════════════════════════════════════════════
prismAtr = ta.atr(i_prismAtrLen)
// percentile rank of the current ATR within its own recent history, 0..1
prismRank = ta.percentrank(prismAtr, i_prismRank) / 100.0
prismMult = math.max(0.2, i_prismBase - i_prismRefr * (1.0 - nz(prismRank, 0.5)))

prismUpRaw = close - prismAtr * prismMult
prismDnRaw = close + prismAtr * prismMult

var float prismUp   = na
var float prismDn   = na
var int   prismDir  = 1
var int   prismFlipBar = na

prismUp := na(prismUp[1]) ? prismUpRaw : (close[1] > prismUp[1] ? math.max(prismUpRaw, prismUp[1]) : prismUpRaw)
prismDn := na(prismDn[1]) ? prismDnRaw : (close[1] < prismDn[1] ? math.min(prismDnRaw, prismDn[1]) : prismDnRaw)

prismDir := na(prismDir[1]) ? 1 : close > nz(prismDn[1], prismDnRaw) ? 1 : close < nz(prismUp[1], prismUpRaw) ? -1 : nz(prismDir[1], 1)
if na(prismFlipBar) or prismDir != nz(prismDir[1], prismDir)
    prismFlipBar := bar_index

prismLine  = prismDir == 1 ? prismUp : prismDn
prismBull  = prismDir == 1
prismAge   = na(prismFlipBar) ? 0 : bar_index - prismFlipBar
prismDist  = math.abs(close - prismLine) / math.max(prismAtr, 1e-9)

prismCol   = prismBull ? i_prismUpCol : i_prismDnCol
pTrail = plot(i_prismOn ? prismLine : na, "Trend Trail", color=color.new(prismCol, 0), linewidth=2, style=plot.style_linebr)
pPrice = plot(i_prismOn and i_prismFill ? close : na, "Trail Fill Ref", color=color.new(#000000, 100), display=display.none)
fill(pTrail, pPrice, color=color.new(prismCol, 88), title="Trail Shade")

// v4.6: the three graded checks, read off values the engine already computes.
// This adds no logic — it names what was already being tested so the reason a
// signal was taken is legible on the arrow instead of only in the dashboard.
prismRegime = prismRank >= 0.75 ? "elevated vol" : prismRank <= 0.25 ? "quiet vol" : "normal vol\"""",
"prism engine")

io.open(P, "w", encoding="utf-8").write(src)
print("\nwrote %d bytes" % len(src))
