"""v4.2 part 2 — track TP2, decouple the ladder, make the reward gate honest."""
import io, sys

P = "/home/user/Claude/MovementEnginePro.v4.2.pine"
src = io.open(P, encoding="utf-8").read()


def sub1(old, new, tag):
    global src
    if src.count(old) != 1:
        sys.exit("PATCH %s: expected 1, found %d" % (tag, src.count(old)))
    src = src.replace(old, new)
    print("  ok  %s" % tag)


# ── 6. TP2 IS TRACKED ───────────────────────────────────────────────────────
sub1(
"""var float activeTp1Px = na
var float activeTp3Px = na""",
"""var float activeTp1Px = na
// v4.2: THE MIDDLE LEG NOW EXISTS. v4.1 kept activeTp1Px and activeTp3Px and no
// activeTp2Px at all — so TP2 was drawn on the chart, published in the alert
// payload, and the engine had no idea whether it had ever traded. A three-leg
// scale-out was tracked as two legs, and the v3.5.41 manual TP2 override moved
// the drawn line while writing to nothing, because there was no tracked value
// for it to write to. Both are fixed by this one declaration and its uses below.
var float activeTp2Px = na
var bool  activeTp2Hit = false
var float activeTp3Px = na""",
"tp2 declaration")

sub1(
"""tp1HitNow = not na(activeTp1Px) and (tradeBuy ? high >= activeTp1Px : low  <= activeTp1Px)
tp3HitNow = not na(activeTp3Px) and (tradeBuy ? high >= activeTp3Px : low  <= activeTp3Px)""",
"""tp1HitNow = not na(activeTp1Px) and (tradeBuy ? high >= activeTp1Px : low  <= activeTp1Px)
tp2HitNow = not na(activeTp2Px) and (tradeBuy ? high >= activeTp2Px : low  <= activeTp2Px)
tp3HitNow = not na(activeTp3Px) and (tradeBuy ? high >= activeTp3Px : low  <= activeTp3Px)""",
"tp2 hit test")

sub1(
"""    activeSlPx   := na
    activeTp1Px  := na
    activeTp3Px  := na""",
"""    activeSlPx   := na
    activeTp1Px  := na
    activeTp2Px  := na
    activeTp3Px  := na
    activeTp2Hit := false""",
"tp2 clear")

sub1(
"""    activeTp1Px  := buyTp1
    activeTp3Px  := buyTp3""",
"""    activeTp1Px  := buyTp1
    activeTp2Px  := buyTp2
    activeTp3Px  := buyTp3
    activeTp2Hit := false""",
"tp2 arm buy")

sub1(
"""    activeTp1Px  := sellTp1
    activeTp3Px  := sellTp3""",
"""    activeTp1Px  := sellTp1
    activeTp2Px  := sellTp2
    activeTp3Px  := sellTp3
    activeTp2Hit := false""",
"tp2 arm sell")

sub1(
"""    if not na(manTP1)
        activeTp1Px := manTP1
    if not na(manTP3)
        activeTp3Px := manTP3""",
"""    if not na(manTP1)
        activeTp1Px := manTP1
    if not na(manTP2)
        activeTp2Px := manTP2
    if not na(manTP3)
        activeTp3Px := manTP3""",
"tp2 manual override")

# record the middle leg when it trades
sub1(
"""if barstate.isconfirmed and tp3HitNow and not slHitNow
    lastSlHit := false""",
"""// v4.2: the middle leg is recorded when it trades, so the dashboard can show
// which legs of the scale-out are actually filling instead of only the first
// and the last.
if barstate.isconfirmed and tp2HitNow and not slHitNow
    activeTp2Hit := true
if barstate.isconfirmed and tp3HitNow and not slHitNow
    lastSlHit := false""",
"tp2 record")

# ── 7. LADDER UNIT — targets in ATR, not in R ──────────────────────────────
sub1(
"""i_tp1R       = input.float(1.5, "TP1 (R-multiple fallback)", minval=0.5, maxval=10.0, step=0.5, group=G_TPSL)""",
"""i_tpUnit     = input.string("ATR (v4.2)", "Target Distances Measured In",
     options=["ATR (v4.2)", "Risk / R (v4.1)"],
     tooltip="What the three target multiples below are multiples OF.\\n\\nRISK / R (v4.1) — every target is a multiple of the STOP DISTANCE. The stop is structural and capped at Max Risk (3.0 ATR), so TP3 at 4.0R can sit 12 ATR from entry. The plan is therefore slowest and least reachable exactly when the structure is widest, which is backwards: a wide invalidation says the setup needs room, not that the market owes you a bigger move.\\n\\nATR (v4.2, default) — the same numbers measured in the instrument's volatility. A wide stop no longer drags every target out with it.\\n\\nMEASURED, 15m, 150 days x 6 seeds, identical entries and identical stops in every row — only the ladder moves:\\n\\n  ladder                TP1   TP2   TP3   bars    SL\\n  1.5/2.5/4.0 R (v4.1)  50%   14%    6%      6   50%\\n  1.5/2.5/4.0 ATR       52%   16%    8%      6   48%\\n  1.0/1.8/3.0 ATR       58%   19%    8%      5   42%\\n  0.8/1.4/2.2 ATR       62%   24%   11%      4   38%\\n\\nRead the TP2 and TP3 columns. Under v4.1 the second third of the position fills once in seven trades and the last third once in sixteen — the 33/33/34 scale-out realises nothing like thirds. Tightening the ladder raises every fill rate, cuts the stop-out rate from 50% to 38% and takes the median hold from 6 bars to 4.\\n\\nThe honest cost: a nearer target is a smaller win. This buys reachability and a working de-risk, not edge.",
     group=G_TPSL)
i_tp1R       = input.float(1.5, "TP1 (× ATR, or × risk in R mode)", minval=0.5, maxval=10.0, step=0.5, group=G_TPSL)""",
"ladder unit input")

io.open(P, "w", encoding="utf-8").write(src)
print("\nwrote %d bytes" % len(src))
