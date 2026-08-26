"""ME Pro v4.1.2 — the manual override is gone. And an honest account of what
could NOT be automated."""
import io, sys, re, shutil

SRC = "/home/user/Claude/MovementEnginePro.v4.1.1.pine"
P = "/home/user/Claude/MovementEnginePro.v4.1.2.pine"
shutil.copy(SRC, P)
src = io.open(P, encoding="utf-8").read()


def sub1(old, new, tag):
    global src
    if src.count(old) != 1:
        sys.exit("PATCH %s: expected 1, found %d" % (tag, src.count(old)))
    src = src.replace(old, new)
    print("  ok  %s" % tag)


HDR = '''// ═══════════════════════════════════════════════════════════════════════════════
// v4.1.2 — NO MANUAL FEATURES. AND TWO THINGS THAT WOULD NOT AUTOMATE.
// ─────────────────────────────────────────────────────────────────────────────
// REMOVED: the Manual TP / SL Override, in full — the toggle, the four price
// inputs, the override applied to the tracked plan, and the drawing code that
// re-pointed the lines and marked the labels with *. Nothing types a level into
// this engine any more. Every stop and every target is computed.
//
// That feature existed because Pine drawings cannot be dragged, so it was the
// closest thing to moving a level by hand. Moving a level by hand is exactly
// what it was: the reward gate had already accepted the setup on the engine's
// own numbers, and a typed target then changed what the trade was scored
// against without changing what it was admitted on. Removing it removes an
// inconsistency, not a capability.
//
// ─────────────────────────────────────────────────────────────────────────────
// WHAT I TRIED TO AUTOMATE AND COULD NOT. Both are reported because a setting
// that survives an honest attempt to derive it is worth more than one nobody
// tested, and because "automated" is a claim I am not going to make falsely.
//
// ATTEMPT 1 — DERIVE THE STOP PAD FROM WICK LENGTH. A stop is taken out by a
// wick, so the pad should track how long wicks currently are:
//
//     pad = c x median( adverse wick / ATR, last 20 bars )
//
// It fails, and not marginally. Measured, 5m, all four modes, both sides:
//
//     rule                    trades/day   med pad    SL   PREMATURE
//     fixed 0.8 (v4.1)              6.81      0.80   36%         28%
//     fixed 1.2 (v4.1.1)            3.98      1.20   42%         15%
//     auto 1.0 x medWick            9.78      0.50   42%         42%
//     auto 1.5 x medWick            8.70      0.50   41%         43%
//     auto 2.0 x medWick            7.64      0.50   41%         41%
//     auto 2.5 x medWick            6.83      0.55   40%         37%
//
// Every auto row pinned to its floor. The median adverse wick is roughly 0.2
// ATR, so even at 2.5x the rule asks for less padding than the measured
// constant, and premature stops go from 15% to over 40%. A single bar's wick is
// simply not the quantity that reaches a stop several bars later. The rule is
// not in this file.
//
// ATTEMPT 2 — COUPLE THE RISK CAP TO THE PAD. v4.1.1 widened the loose-anchor
// pad and trade count fell 6.81 -> 3.98/day. I told you that was the Max Risk
// Cap rejecting the wider stops and to raise it by hand. That was wrong, and
// deriving it exposed the error:
//
//     pad 1.2  cap 3.0    3.98/day    SL 42%   premature 15%
//     pad 1.2  cap 3.4    4.10/day    SL 41%   premature 16%
//     pad 1.2  cap 3.8    4.10/day    SL 41%   premature 16%
//     pad 1.2  cap 4.2    4.10/day    SL 41%   premature 16%
//
// Flat. The cap was recovering 28 trades out of 679 lost. Almost nothing sits
// between 3.0 and 4.2 ATR of risk, so coupling the cap automates a lever that
// does not move.
//
// WHERE THE TRADES ACTUALLY WENT — THE REWARD GATE. A wider stop is a bigger R,
// and TP1 is a fixed distance in price. So the same target becomes a SMALLER
// multiple of risk and the reward floor rejects it. The pad and the reward gate
// are coupled through arithmetic, and nothing in the engine says so.
//
// This is the same defect class the v5.x line found from the other direction:
// the reward gate rejecting a trade for a property of its TARGET rather than of
// the setup. It is NOT fixed here, because fixing it changes which setups the
// engine admits and that belongs in its own version with its own before/after —
// shipping it inside a release whose stated purpose is removing a feature would
// be exactly the kind of silent change this file exists to stop.
//
// SO THE STOP PAD STAYS A MEASURED CONSTANT. Not because automation was not
// attempted, but because it was, twice, and the constant beat both attempts on
// the column that matters. It is a number derived from measurement rather than
// a dial you are expected to tune, which is the honest version of "automatic".
//
// ─────────────────────────────────────────────────────────────────────────────
// STILL AUTOMATIC, and unchanged from v4.1 — listed so the claim is checkable:
// HTF timeframe selection, FRVP window in hours, the volatility multiplier on
// the stop, the adaptive order-flow threshold, the scalp timeframe calibration,
// the degenerate-volume bypass, the Heikin Ashi guard, breakeven after TP1, the
// TP ladder with its spacing and ceiling rules, and the per-family stop anchor
// added in v4.1.1.
//
// Counts and outcome geometry only. No expectancy computed or quoted; synthetic
// data, no price feed reachable.
// ═══════════════════════════════════════════════════════════════════════════════

'''

sub1("// ═══════════════════════════════════════════════════════════════════════════════\n// v4.1.1 — THREE DEFECTS IN v4.1, MEASURED AND FIXED. NOTHING ELSE CHANGED.",
     HDR + "// ═══════════════════════════════════════════════════════════════════════════════\n// v4.1.1 — THREE DEFECTS IN v4.1, MEASURED AND FIXED. NOTHING ELSE CHANGED.",
     "header")

# ── remove the manual inputs ──────────────────────────────────────────────
start = src.index('i_manualOn   = input.bool(false, "Manual TP / SL Override",')
end = src.index('i_tpslShow   = input.bool(true, "Show TP / SL Lines",')
src = src[:start] + src[end:]
print("  ok  manual inputs removed")

# ── remove the override block ─────────────────────────────────────────────
start = src.index("// ═══════════════════════════════════════════════════════════════════════════════\n// v3.5.41 MANUAL LEVEL OVERRIDE")
end = src.index("// ═══════════════════════════════════════════════════════════════════════════════\n// SIGNAL LABELS")
src = src[:start] + src[end:]
print("  ok  manual override block removed")

src = src.replace('indicator("Movement Engine Pro v4.1.1", shorttitle="ME Pro v4.1.1"',
                  'indicator("Movement Engine Pro v4.1.2", shorttitle="ME Pro v4.1.2"')
src = src.replace('// © ME Institutional — Movement Engine Pro v4.1.1 (the label and the stop now describe the same trade)',
                  '// © ME Institutional — Movement Engine Pro v4.1.2 (nothing is typed in any more)')
src = src.replace('"ME PRO v4.1.1"', '"ME PRO v4.1.2"')

io.open(P, "w", encoding="utf-8").write(src)
print("\nwrote %d bytes" % len(src))
for tok in ("i_manualOn", "i_mSL", "manSL", "manTP1", "manTP2", "manTP3"):
    n = src.count(tok)
    print("  %-12s remaining references: %d" % (tok, n))
