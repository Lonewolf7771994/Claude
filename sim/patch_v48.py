"""ME Pro v4.8 — the gate default that the trail made correct."""
import io, sys, shutil

SRC = "/home/user/Claude/MovementEnginePro.v4.7.pine"
P = "/home/user/Claude/MovementEnginePro.v4.8.pine"
shutil.copy(SRC, P)
src = io.open(P, encoding="utf-8").read()


def sub1(old, new, tag):
    global src
    if src.count(old) != 1:
        sys.exit("PATCH %s: expected 1, found %d" % (tag, src.count(old)))
    src = src.replace(old, new)
    print("  ok  %s" % tag)


sub1('i_revGate    = input.string("Leg + trend + HTF", "No-Reversal Gate",',
     'i_revGate    = input.string("Leg only", "No-Reversal Gate",',
     "gate default")

sub1("""     tooltip="v4.4: how strictly a trade must agree with the direction already in progress.""",
     """     tooltip="v4.8 CHANGED THE DEFAULT TO 'Leg only', and the reason is that v4.6's trail made the trend half redundant.\\n\\nMEASURED, 15m, 150 days x 4 seeds, every other v4.7 default held:\\n\\n  gate setting             signals/day   vs default\\n  Leg + trend + HTF (v4.7)       0.28         1.0x\\n  Leg + trend + HTF, ER 0.20     0.48         1.7x\\n  Leg only                       0.80         2.8x\\n\\nAt the v4.7 default the engine converted 1.44% of triggers and produced ONE TRADE EVERY THREE TO FOUR DAYS. The efficiency-ratio condition alone appeared in 78% of all blocked triggers — the single largest cause in the whole stack, ahead of the body filter at 73%.\\n\\nWHY DROPPING IT IS NOT JUST LOOSENING. The ER test existed to stop 'with the leg' being meaningless, because the leg was `close > close[20]` — a comparison that can read UP in pure chop whenever the bar 20 back happens to be lower. Since v4.6 the leg is the TRAIL, which only flips on a close through a level that has been ratcheting one way. It cannot be 'up' in chop the way the naive comparison could. The trail already does what the ER filter was added to do.\\n\\nThe leakage audit is unchanged and still reads EXACTLY ZERO at this level: a long requires the trail in its up state, so a long against the trend cannot pass. You keep the no-reversal guarantee and get 2.8x the trades.\\n\\nRaise it back to 'Leg + trend + HTF' if you want the stricter reading and accept roughly a third of the trades.\\n\\nORIGINAL v4.4 NOTE FOLLOWS — how strictly a trade must agree with the direction already in progress.""",
     "gate tooltip")

# ER default relaxed too, for anyone who does re-enable the trend level
sub1('i_revErMin   = input.float(0.32, "  Gate: Min Efficiency Ratio", minval=0.0, maxval=0.9, step=0.01,',
     'i_revErMin   = input.float(0.22, "  Gate: Min Efficiency Ratio", minval=0.0, maxval=0.9, step=0.01,',
     "er default")

sub1("""     tooltip="v4.4: how directional the market must be before a 'continuation' trade is allowed to mean anything.""",
     """     tooltip="v4.8 DEFAULT 0.32 -> 0.22. At 0.32 this condition appeared in 78% of every blocked trigger, the largest single cause in the engine, and it is only consulted at gate levels above 'Leg only'. Measured on 15m: moving it 0.32 -> 0.20 alone took the rate from 0.28 to 0.48 signals/day.\\n\\nv4.4 NOTE — how directional the market must be before a 'continuation' trade is allowed to mean anything.""",
     "er tooltip")

# Engine Mode is inert while the gate requires HTF — say so where it is chosen
sub1("""     tooltip="v4.1: ALL FOUR TRIGGERS (MSS, FVG, sweep, band rejection) are live in EVERY mode.""",
     """     tooltip="v4.8 MEASURED CAVEAT, READ THIS FIRST. While the No-Reversal Gate is set to any level that includes HTF, THIS SETTING BARELY MATTERS. Balanced and Strict gate on HTF agreement, and the no-reversal gate already requires it — so the mode's own test is subsumed. Measured on 15m with every other default held, switching Balanced to Aggressive moved the rate from 0.28 to 0.28 signals/day, a change of 1.0x. Exactly nothing.\\n\\nThe mode becomes meaningful again at gate level 'Leg only' (the v4.8 default), which does not test HTF itself.\\n\\nv4.1 NOTE — ALL FOUR TRIGGERS (MSS, FVG, sweep, band rejection) are live in EVERY mode.""",
     "mode caveat")

io.open(P, "w", encoding="utf-8").write(src)
print("\nwrote %d bytes" % len(src))
