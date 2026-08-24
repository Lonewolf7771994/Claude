"""v4.5 — the structural trail, and the plan that updates on the chart."""
import io, sys

P = "/home/user/Claude/MovementEnginePro.v4.5.pine"
src = io.open(P, encoding="utf-8").read()


def sub1(old, new, tag):
    global src
    if src.count(old) != 1:
        sys.exit("PATCH %s: expected 1, found %d" % (tag, src.count(old)))
    src = src.replace(old, new)
    print("  ok  %s" % tag)


# ── remember the ORIGINAL risk, which the trail is measured against ────────
sub1("""var bool  activeAtBe   = false""",
     """var bool  activeAtBe   = false
// v4.5: the stop MOVES now, so the original risk has to be kept separately —
// measuring the trail trigger against a stop that is itself trailing would be
// circular and the threshold would drift as the trade ran.
var float activeR0     = na
var bool  activeTrailOn = false""",
     "original risk var")

for side, px in (("buy", "buySLpx"), ("sell", "sellSLpx")):
    sub1("""    activeEntryConf := %sAligned
    activeTp1Hit := false""" % side,
         """    activeEntryConf := %sAligned
    activeR0     := math.abs(%sEntryRef - %s)
    activeTrailOn := false
    activeTp1Hit := false""" % (side, side, px),
         "record r0 %s" % side)

sub1("""    activeTp1Hit := false
    activeAtBe   := false
    activeBeOk   := false
    tradeStartBar := na""",
     """    activeTp1Hit := false
    activeAtBe   := false
    activeBeOk   := false
    activeR0     := na
    activeTrailOn := false
    tradeStartBar := na""",
     "clear r0")

# ── THE TRAIL ──────────────────────────────────────────────────────────────
sub1(
"""if barstate.isconfirmed and tp3HitNow and not slHitNow
    lastSlHit := false""",
"""// ═══════════════════════════════════════════════════════════════════════════════
// v4.5 STRUCTURAL TRAIL — the stop stops being frozen at the entry bar
// ─────────────────────────────────────────────────────────────────────────────
// Until now the stop was placed at entry and never moved again except the single
// jump to breakeven. A plan that ran three ATR in favour still carried its
// original invalidation, so an entire winning move could be handed back to a
// level that had long stopped describing anything.
//
// The trail is STRUCTURAL rather than a fixed distance: it sits a buffer beyond
// the last CONFIRMED pivot, so it advances only when the market actually builds a
// higher floor under a long. A fixed-distance trail tightens on every bar
// regardless of whether anything was built, which is how a trend trade gets
// shaken out of a move that never broke structure.
//
// Two guards. It engages only once the trade is i_trailStart x its ORIGINAL risk
// onside — measuring against the live stop would be circular, since that is the
// thing being moved. And it can only ever tighten: math.max for a long, so a
// stop that has advanced never retreats. A stop that widens is not a stop.
// ═══════════════════════════════════════════════════════════════════════════════
if barstate.isconfirmed and i_trailOn and not na(activeSlPx) and not na(activeR0) and activeR0 > 0
    float prog = tradeBuy ? (close - activeEntryPx) / activeR0 : (activeEntryPx - close) / activeR0
    if prog >= i_trailStart
        activeTrailOn := true
    if activeTrailOn
        float anchor = tradeBuy ? lastPL : lastPH
        if not na(anchor)
            float cand = tradeBuy ? anchor - atr14 * i_trailBuf : anchor + atr14 * i_trailBuf
            // never loosen, and never trail through the current price
            if tradeBuy and cand > activeSlPx and cand < close
                activeSlPx := cand
            if not tradeBuy and cand < activeSlPx and cand > close
                activeSlPx := cand

if barstate.isconfirmed and tp3HitNow and not slHitNow
    lastSlHit := false""",
"trail logic")

# ── THE CHART UPDATES ─────────────────────────────────────────────────────
sub1(
"""// ═══════════════════════════════════════════════════════════════════════════════
// SIGNAL LABELS""",
"""// ═══════════════════════════════════════════════════════════════════════════════
// v4.5 THE PLAN UPDATES ON THE CHART
// ─────────────────────────────────────────────────────────────────────────────
// The lines were drawn once at the entry bar with a fixed right edge and then
// left alone, so a live plan showed a stop that had already moved and stopped
// short of the bar the trade was actually on. With a trailing stop that is not a
// cosmetic problem — the drawn level would simply be the wrong number.
//
// Every bar the trade is open: the lines extend to the current bar, the stop line
// and its label follow the level actually in force, and the target labels ride
// along with them. The label reads BE once the stop is at entry and TRAIL once
// structure has carried it past that.
// ═══════════════════════════════════════════════════════════════════════════════
if i_tpslShow and not na(activeSlPx) and not na(tpsl_sl)
    int xr = bar_index + 2
    line.set_x2(tpsl_sl, xr)
    line.set_y1(tpsl_sl, activeSlPx)
    line.set_y2(tpsl_sl, activeSlPx)
    if not na(tpsl_ent)
        line.set_x2(tpsl_ent, xr)
    if not na(tpsl_tp1)
        line.set_x2(tpsl_tp1, xr)
    if not na(tpsl_tp2)
        line.set_x2(tpsl_tp2, xr)
    if not na(tpsl_tp3)
        line.set_x2(tpsl_tp3, xr)
    if not na(tpsl_slL)
        stopWord = activeTrailOn and activeSlPx != activeEntryPx ? " TRAIL" : activeAtBe ? " BE   " : " SL   "
        label.set_x(tpsl_slL, xr)
        label.set_y(tpsl_slL, activeSlPx)
        label.set_text(tpsl_slL, stopWord + sigTag + str.tostring(activeSlPx, format.mintick))
    if not na(tpsl_tp1L)
        label.set_x(tpsl_tp1L, xr)
    if not na(tpsl_tp2L)
        label.set_x(tpsl_tp2L, xr)
    if not na(tpsl_tp3L)
        label.set_x(tpsl_tp3L, xr)
    if not na(tpsl_slZ)
        box.set_right(tpsl_slZ, xr)
        box.set_top(tpsl_slZ, activeSlPx + atr14 * i_zoneAtr)
        box.set_bottom(tpsl_slZ, activeSlPx - atr14 * i_zoneAtr)
    if not na(tpsl_tp1Z)
        box.set_right(tpsl_tp1Z, xr)
    if not na(tpsl_tp2Z)
        box.set_right(tpsl_tp2Z, xr)
    if not na(tpsl_tp3Z)
        box.set_right(tpsl_tp3Z, xr)

// ═══════════════════════════════════════════════════════════════════════════════
// SIGNAL LABELS""",
"chart update")

# ── DASHBOARD: show the measured distribution ─────────────────────────────
sub1(
"""    table.cell(dash, 0, 15, "Risk Dist", text_color=dim, text_size=size.tiny, text_halign=text.align_left, bgcolor=color.rgb(12, 12, 18))""",
"""    // v4.5: what the market actually said, in its own volatility units, and how
    // big a sample that came from. If this reads "warming up" the engine is on
    // the fixed ladder because it does not yet have enough resolved history.
    qTxt = qReady ? "q" + str.tostring(i_qTp1, "#") + " " + str.tostring(math.round(qUp1, 2)) + "  q" + str.tostring(i_qTp3, "#") + " " + str.tostring(math.round(qUp3, 2)) + " ATR" : "warming up"
    table.cell(dash, 0, 15, "Measured move (n=" + str.tostring(array.size(mfeUp)) + ")", text_color=dim, text_size=size.tiny, text_halign=text.align_left, bgcolor=color.rgb(12, 12, 18))
    f_cell(1, 15, qTxt, qReady ? grn : yel)
    f_cell(2, 15, qReady ? "q" + str.tostring(i_qTp1, "#") + " " + str.tostring(math.round(qDn1, 2)) + "  q" + str.tostring(i_qTp3, "#") + " " + str.tostring(math.round(qDn3, 2)) + " ATR" : "fixed ladder", qReady ? red_ : yel)

    table.cell(dash, 0, 16, "Risk Dist", text_color=dim, text_size=size.tiny, text_halign=text.align_left, bgcolor=color.rgb(12, 12, 18))""",
"dashboard quantile row")

io.open(P, "w", encoding="utf-8").write(src)
print("\nwrote %d bytes" % len(src))
