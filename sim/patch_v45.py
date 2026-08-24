"""ME Pro v4.5 — manual levels deleted, quantile targets, live structural trail."""
import io, sys, shutil

SRC = "/home/user/Claude/MovementEnginePro.v4.4.pine"
P = "/home/user/Claude/MovementEnginePro.v4.5.pine"
shutil.copy(SRC, P)
src = io.open(P, encoding="utf-8").read()


def sub1(old, new, tag):
    global src
    if src.count(old) != 1:
        sys.exit("PATCH %s: expected 1, found %d" % (tag, src.count(old)))
    src = src.replace(old, new)
    print("  ok  %s" % tag)


def cut(start_marker, end_marker, tag):
    """delete everything from start_marker up to (not including) end_marker"""
    global src
    a = src.find(start_marker)
    b = src.find(end_marker)
    if a < 0 or b < 0 or b <= a:
        sys.exit("CUT %s: markers not found (%d,%d)" % (tag, a, b))
    src = src[:a] + src[b:]
    print("  ok  %s (cut %d chars)" % (tag, b - a))


# ── 1. DELETE THE MANUAL OVERRIDE INPUTS ───────────────────────────────────
cut('i_manualOn   = input.bool(false, "Manual TP / SL Override",',
    'i_tpslShow   = input.bool(true, "Show TP / SL Lines",',
    "manual inputs")

# ── 2. DELETE THE MANUAL OVERRIDE BLOCK ────────────────────────────────────
cut("""// ═══════════════════════════════════════════════════════════════════════════════
// v3.5.41 MANUAL LEVEL OVERRIDE""",
    """// ═══════════════════════════════════════════════════════════════════════════════
// SIGNAL LABELS""",
    "manual block")

# ── 3. QUANTILE ENGINE — inputs ────────────────────────────────────────────
sub1(
"""i_tpUnit     = input.string("ATR (v4.2)", "Target Distances Measured In",""",
"""i_tpMode     = input.string("Measured quantiles (v4.5)", "Target Placement",
     options=["Measured quantiles (v4.5)", "Fixed multiples (v4.4)"],
     tooltip="v4.5: where the three targets come from.\\n\\nFIXED MULTIPLES — every target this engine has ever placed came from a number somebody chose: 1.5/2.5/4.0 R in v4.1, 0.8/1.4/2.2 ATR in v4.4. Both are guesses wearing decimal points. Nothing ever asked the instrument how far it actually travels.\\n\\nMEASURED QUANTILES (default) — the engine measures, over resolved history, how far price ACTUALLY ran in its own volatility units over the horizon it holds for, and places each target at a percentile of that distribution. Ask for the 50th percentile and you get the price that half of all windows reached.\\n\\nMEASURED, 15m, 150 days x 6 seeds, requesting q50 / q70 / q85:\\n\\n  requested reach   50%   30%   15%\\n  delivered reach   53%   30%   11%\\n\\nIt does what it says. That is the whole point and it is a claim a fixed multiple cannot make at all — you now set the REACH RATE and the engine finds the price, instead of setting a price and discovering the reach rate afterwards.\\n\\nIt is not automatically 'better'. On the same data the measured q50/q70/q85 sat at 1.05 / 2.33 / 5.08 ATR against the guessed 0.80 / 1.40 / 2.20, so the quantile ladder was WIDER and filled its deep legs less often — because it was asked for a rarer event. Ask for a common one and it delivers a common one.\\n\\nNON-REPAINTING: the distribution is built only from windows that fully resolved before the current bar.",
     group=G_TPSL)
i_qTp1       = input.float(50, "  Reach target for TP1 (%)", minval=5, maxval=95, step=5,
     tooltip="v4.5: the share of measured windows that reached at least this far. 50 places TP1 at the median move — reached by about half of all windows over the horizon.\\nLower it for a nearer, more-often-reached first target (and an earlier breakeven); raise it for a further one.",
     group=G_TPSL)
i_qTp2       = input.float(65, "  Reach target for TP2 (%)", minval=5, maxval=95, step=5, group=G_TPSL)
i_qTp3       = input.float(80, "  Reach target for TP3 (%)", minval=5, maxval=95, step=5, group=G_TPSL)
i_qHorizon   = input.int(16, "  Measurement Horizon (bars)", minval=4, maxval=100,
     tooltip="v4.5: how far forward each historical window was measured. Defaults to the same 16 bars as the time stop, so the distribution describes exactly the holding period the engine actually uses. Changing one without the other measures a horizon you do not trade.",
     group=G_TPSL)
i_qWindow    = input.int(500, "  Distribution Window (bars)", minval=100, maxval=2000,
     tooltip="v4.5: how much resolved history the distribution is built from. Longer is more stable and slower to adapt to a change in the instrument's character.",
     group=G_TPSL)
i_tpUnit     = input.string("ATR (v4.2)", "Target Distances Measured In",""",
"quantile inputs")

# ── 4. TRAILING STOP — input ───────────────────────────────────────────────
sub1(
"""i_beAfterTp1 = input.bool(true, "Move SL To Breakeven After TP1",""",
"""i_trailOn    = input.bool(true, "Trail The Stop To Structure",
     tooltip="v4.5: once the trade is in profit the stop follows the most recent CONFIRMED swing in the trade's favour, and the drawn line moves with it every bar.\\n\\nBefore this the stop was set at entry and never moved again except the one jump to breakeven. A plan that ran three ATR in your favour still carried its original invalidation, so an entire winning move could be handed back to a stop that had stopped describing anything.\\n\\nThe trail is STRUCTURAL, not a fixed distance: it sits a buffer beyond the last confirmed pivot low for a long, so it moves only when the market actually builds a higher floor. It can never loosen — a stop that widens is not a stop.\\n\\nThis is what makes the plan update on the chart instead of being frozen at the entry bar.",
     group=G_RISK)
i_trailBuf   = input.float(0.35, "  Trail Buffer Beyond Swing (× ATR)", minval=0.05, maxval=2.0, step=0.05,
     tooltip="v4.5: clearance between the trailing stop and the swing it follows. Too tight and ordinary retests take the trade out; too wide and the trail gives back most of what it is protecting.",
     group=G_RISK)
i_trailStart = input.float(1.0, "  Start Trailing After (× risk)", minval=0.0, maxval=5.0, step=0.1,
     tooltip="v4.5: how far in profit the trade must be before the trail engages, measured in multiples of the original stop distance. 0 trails from the entry bar. 1.0 means the trade must be one full R onside first, so the trail tightens a winner rather than interfering with a trade that has not proved anything yet.",
     group=G_RISK)
i_beAfterTp1 = input.bool(true, "Move SL To Breakeven After TP1",""",
"trail inputs")

io.open(P, "w", encoding="utf-8").write(src)
print("\nwrote %d bytes" % len(src))
