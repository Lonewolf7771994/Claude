"""v4.3 — apply the no-reversal gate and close the counter-trend exemption."""
import io, sys

P = "/home/user/Claude/MovementEnginePro.v4.3.pine"
src = io.open(P, encoding="utf-8").read()


def sub1(old, new, tag):
    global src
    if src.count(old) != 1:
        sys.exit("PATCH %s: expected 1, found %d" % (tag, src.count(old)))
    src = src.replace(old, new)
    print("  ok  %s" % tag)


# ── THE COUNTER-TREND EXEMPTION ────────────────────────────────────────────
# v3.5.1 exempted sweep (and v4.0 band) scalps from the CVD and momentum gates
# BECAUSE those setups fire against the prevailing direction. That exemption is
# the mechanism by which this engine takes reversal trades at all.
sub1(
"""cvdOkBuy   = not volDataSeen or cvdBull  or (isScalp and (buyTrigSweep  or buyTrigBand))
cvdOkSell  = not volDataSeen or cvdBear  or (isScalp and (sellTrigSweep or sellTrigBand))
momOkBuyEff  = momOkBuy  or (isScalp and (buyTrigSweep  or buyTrigBand))
momOkSellEff = momOkSell or (isScalp and (sellTrigSweep or sellTrigBand))""",
"""// ═══════════════════════════════════════════════════════════════════════════════
// v4.3 — THE EXEMPTION IS WHAT MADE THESE REVERSAL TRADES
// ─────────────────────────────────────────────────────────────────────────────
// v3.5.1 exempted sweep scalps from the CVD and momentum gates, and its reason
// was explicit: "a bullish sweep at a low happens AFTER a decline — CVD and
// momentum are still bearish at that moment, so sweep scalps were vetoed
// essentially 100% of the time". v4.0 extended the same exemption to band
// rejections for the same reason.
//
// That reasoning is correct AND it is the precise mechanism by which this engine
// takes counter-trend trades. The trigger shape was never the issue: a bull
// sweep taken while the leg is DOWN is a reversal, and the identical sweep taken
// while the leg is UP is a pullback that resumed. What decided which one you got
// was this exemption.
//
// So under the no-reversal gate the exemption is withdrawn — but only there,
// because without it the sweep and band triggers genuinely cannot fire at all,
// which is the v3.5.1 defect being re-created. With the gate off, v4.2 behaviour
// is preserved byte for byte.
// ═══════════════════════════════════════════════════════════════════════════════
revExempt  = not i_noReversal
cvdOkBuy   = not volDataSeen or cvdBull  or (isScalp and revExempt and (buyTrigSweep  or buyTrigBand))
cvdOkSell  = not volDataSeen or cvdBear  or (isScalp and revExempt and (sellTrigSweep or sellTrigBand))
momOkBuyEff  = momOkBuy  or (isScalp and revExempt and (buyTrigSweep  or buyTrigBand))
momOkSellEff = momOkSell or (isScalp and revExempt and (sellTrigSweep or sellTrigBand))

// THE GATE ITSELF. A trade must run with the leg in progress.
nonRevOkBuy  = not i_noReversal or legUp
nonRevOkSell = not i_noReversal or legDown""",
"exemption and gate")

# ── APPLY THE GATE TO THE SIGNAL ───────────────────────────────────────────
sub1(
"""rawBuyPre  = barstate.isconfirmed and buyTrigger  and barBull and strongBull and notWeakBuy  and ofBull and cvdOkBuy  and momOkBuyEff  and modePassBull and biasOkBuy  and coolOk and riskOkBuy  and rsiOkBuy  and newsOk and breakerOk and chaseOkBuy  and inSession and regimeOk
rawSellPre = barstate.isconfirmed and sellTrigger and barBear and strongBear and notWeakSell and ofBear and cvdOkSell and momOkSellEff and modePassBear and biasOkSell and coolOk and riskOkSell and rsiOkSell and newsOk and breakerOk and chaseOkSell and inSession and regimeOk""",
"""rawBuyPre  = barstate.isconfirmed and buyTrigger  and barBull and strongBull and notWeakBuy  and ofBull and cvdOkBuy  and momOkBuyEff  and modePassBull and biasOkBuy  and coolOk and riskOkBuy  and rsiOkBuy  and newsOk and breakerOk and chaseOkBuy  and inSession and regimeOk and nonRevOkBuy
rawSellPre = barstate.isconfirmed and sellTrigger and barBear and strongBear and notWeakSell and ofBear and cvdOkSell and momOkSellEff and modePassBear and biasOkSell and coolOk and riskOkSell and rsiOkSell and newsOk and breakerOk and chaseOkSell and inSession and regimeOk and nonRevOkSell""",
"signal gate")

# ── BLOCK REASONS ─────────────────────────────────────────────────────────
sub1("""    r += regimeOk ? "" : "regime "
    if r != ""
        lastBlockReason := "BUY ✕ " + r""",
     """    r += regimeOk ? "" : "regime "
    r += nonRevOkBuy ? "" : "reversal "
    if r != ""
        lastBlockReason := "BUY ✕ " + r""",
     "block reason buy")

sub1("""    r += regimeOk ? "" : "regime "
    if r != ""
        lastBlockReason := "SELL ✕ " + r""",
     """    r += regimeOk ? "" : "regime "
    r += nonRevOkSell ? "" : "reversal "
    if r != ""
        lastBlockReason := "SELL ✕ " + r""",
     "block reason sell")

# ── TRIGGER MEMORY includes the POC event ─────────────────────────────────
sub1("anyTrigEvent = mssUpEvent or mssDownEvent or fvgRetestBull or fvgRetestBear or sweepBullEvent or sweepBearEvent",
     "anyTrigEvent = mssUpEvent or mssDownEvent or fvgRetestBull or fvgRetestBear or sweepBullEvent or sweepBearEvent or pocBullEvent or pocBearEvent",
     "trigger memory")

# ── DASHBOARD: replace the now-redundant CVD row with a profile/flow row ──
sub1(
"""    table.cell(dash, 0, 11, "CVD Flow", text_color=dim, text_size=size.tiny, text_halign=text.align_left, bgcolor=color.rgb(12, 12, 18))
    f_cell(1, 11, not volDataSeen ? "OFF (no vol)" : cvdBull ? "BULL" : "BEAR", not volDataSeen ? dim : cvdBull ? grn : red_)
    f_cell(2, 11, not volDataSeen ? "OFF (no vol)" : cvdBull ? "BULL" : "BEAR", not volDataSeen ? dim : cvdBull ? grn : red_)""",
"""    // v4.3: CVD, the leg, absorption and the POC trigger — the order-flow and
    // volume-profile readings, in the one row that used to show CVD alone.
    cvdTxt = not volDataSeen ? "OFF" : cvdBull ? "CVD▲" : "CVD▼"
    legTxt2 = legUp ? "leg▲" : legDown ? "leg▼" : "leg—"
    flowTxt = cvdTxt + "  " + legTxt2 + (absorbing ? "  ABSORB" : "")
    table.cell(dash, 0, 11, i_noReversal ? "Flow · no-reversal" : "Flow", text_color=dim, text_size=size.tiny, text_halign=text.align_left, bgcolor=color.rgb(12, 12, 18))
    f_cell(1, 11, flowTxt + (pocBull ? "  POC▲" : ""), nonRevOkBuy  ? grn  : dim)
    f_cell(2, 11, flowTxt + (pocBear ? "  POC▼" : ""), nonRevOkSell ? red_ : dim)""",
"dashboard flow row")

# ── TITLE ────────────────────────────────────────────────────────────────
sub1('indicator("Movement Engine Pro v4.2", shorttitle="ME Pro v4.2"',
     'indicator("Movement Engine Pro v4.3", shorttitle="ME Pro v4.3"',
     "title")
sub1('// © ME Institutional — Movement Engine Pro v4.2 (one trigger, one ladder, one gate)',
     '// © ME Institutional — Movement Engine Pro v4.3 (profile, flow, no reversal)',
     "copyright")
sub1('(isHeikin ? "⛔ HEIKIN ASHI — LEVELS INVALID" : "ME PRO v4.2")',
     '(isHeikin ? "⛔ HEIKIN ASHI — LEVELS INVALID" : "ME PRO v4.3")',
     "dash title")

io.open(P, "w", encoding="utf-8").write(src)
print("\nwrote %d bytes" % len(src))
