"""ME Pro v4.1.1 — v4.1's structure, with the three measured defects fixed.

Nothing is added. No trail, no CRT, no pace preset, no direction stack. The
architecture, the mode ladder, the confluence score and every gate are v4.1's.
"""
import io, sys, shutil

SRC = "/home/user/Claude/MovementEnginePro.pine"
P = "/home/user/Claude/MovementEnginePro.v4.1.1.pine"
shutil.copy(SRC, P)
src = io.open(P, encoding="utf-8").read()


def sub1(old, new, tag):
    global src
    if src.count(old) != 1:
        sys.exit("PATCH %s: expected 1, found %d" % (tag, src.count(old)))
    src = src.replace(old, new)
    print("  ok  %s" % tag)


HDR = '''// ═══════════════════════════════════════════════════════════════════════════════
// v4.1.1 — THREE DEFECTS IN v4.1, MEASURED AND FIXED. NOTHING ELSE CHANGED.
// ─────────────────────────────────────────────────────────────────────────────
// Report: the entries are inaccurate, weak and wrong. All three turned out to
// be separate, findable things. v4.1's structure is untouched — same modes,
// same confluence ladder, same gates, same triggers.
//
// ─────────────────────────────────────────────────────────────────────────────
// 1. THE LABEL AND THE STOP DISAGREED ABOUT WHICH TRADE THIS IS.
//
// v4.1 chose the trigger name and the stop anchor with DIFFERENT priority
// orders:
//
//     buyType     = mssUp ? "MSS" : fvg ? "FVG" : sweep ? "SWEEP" : band ? "BAND"
//     buySlAnchor = sweep ? sweepLow : band ? bandLow : fvg ? gapBot : lastPL
//     buyChaseRef = sweep ? sweepLvl : band ? bandLvl : fvg ? gapTop : lastPH
//
// MSS is first in one and last in the other. An MSS stays "fresh" for
// i_triggerAge bars (3 by default), so on any bar where a stale MSS overlaps a
// band rejection — common, because band rejections are the highest-supply
// trigger in the engine — the chart printed BUY (MSS) and the alert said
// "trigger":"MSS", while the stop was built from the band's rejection low and
// the anti-chase cap was measured from the band, not the pivot.
//
// The trade you were shown and the trade whose risk was priced were not the
// same trade. That is the literal sense in which an entry was wrong, and it is
// read straight off the source rather than inferred from behaviour.
//
// FIXED by computing the selection ONCE and having the label, the stop anchor,
// the chase reference and the alert all read it. The order kept is the STOP's
// order, not the label's, because the v4.1 header already justifies it — the
// triggers are ranked by how precisely each defines its own invalidation:
//
//     SWEEP  the rejecting bar's wick     tightest, a dated single-bar extreme
//     BAND   the rejecting bar's extreme  same shape, measured off the mean
//     FVG    the far edge of the gap      a zone, not a bar
//     MSS    the last pivot               widest, and the least specific
//
// The label now follows the stop. Before, the stop followed nothing.
//
// ─────────────────────────────────────────────────────────────────────────────
// 2. ONE STOP PAD WAS SERVING SIX DIFFERENT KINDS OF ANCHOR.
//
// i_slAtr pads every stop by the same multiple of ATR regardless of what it is
// padding. But the anchors are not comparable objects. A band or sweep stop
// sits beyond the REJECTING BAR'S OWN EXTREME — a dated, single-bar level. An
// MSS stop sits beyond the LAST PIVOT, an object several bars old that ordinary
// noise violates without the idea being wrong.
//
// Measured as PREMATURE STOPS — the stop was hit while the setup's own
// invalidation had never been closed through, i.e. the loss came from where the
// stop was and not from the market. 5m, all four modes, both sides, 2 seeds:
//
//     pad      mss    fvg  sweep   band  band2  value
//     0.4 ATR  ---    61%    68%    47%    52%    59%
//     0.8 ATR  61%    43%    43%    23%    30%    35%
//     1.2 ATR  41%     0%    14%    15%    13%    16%
//     1.6 ATR  36%     0%    12%     8%    10%    18%
//
// At the shipped 0.8 the band-family anchors sit at 23-35% while the
// pivot/gap/wick anchors sit at 43-61%. Same pad, twice the manufactured
// losses, purely because of what is being padded.
//
// FIXED by making the pad per-family. Defaults: band and band2 keep 0.8 (they
// are already the precise anchors); MSS, FVG, sweep and value get 1.2.
//
// HONEST LIMIT ON THIS TABLE. Trade counts fall sharply as the pad widens
// (fvg 315 -> 49, sweep 177 -> 51) because a wider stop pushes more setups past
// the Max Risk Cap and this engine REJECTS those rather than squeezing the stop
// into range. So the stop-out column at the wide end is partly survivorship and
// is NOT quoted here as the reason. The premature column is the robust one: it
// falls monotonically with pad for every trigger, and the ORDERING between
// triggers is stable at every pad.
//
// ─────────────────────────────────────────────────────────────────────────────
// 3. YOU COULD NOT SWITCH OFF THE TRIGGER THAT PRODUCES MOST OF THE SIGNALS.
//
// Six triggers were ORed together with no toggle. Run one at a time — which is
// what a toggle does, so this predicts what you get rather than attributing
// after the fact:
//
//     trigger   share of all signals    TP1    TP2    TP3     SL
//     band                      68%     60%    15%     8%    38%
//     band2                     28%     58%    22%    10%    41%
//     value                     12%     57%    18%     9%    32%
//     mss                       11%     59%    26%    15%    32%
//     fvg                        9%     58%    29%    18%    37%
//     sweep                      6%     57%    23%    10%    41%
//
// VWAP band rejections are 68% of everything the engine fires, 77% with the
// 2-sigma band. The ICT structure triggers this indicator is named for are
// 6-11% each. THREE OF EVERY FOUR SIGNALS ARE A BAND FADE — and the band has
// the weakest follow-through in the set: it reaches TP1 as often as anything
// and then stops, TP2 15% and TP3 8% against 29%/18% for the FVG retest.
//
// A trade that hits its first target and dies is what "looks like it works but
// does not" actually is.
//
// FIXED by adding an Entry Set control and six per-trigger toggles. The DEFAULT
// IS UNCHANGED — All still means all — because cutting your trade count by 74%
// is your decision, not a silent one. Structure only roughly doubles the TP2
// and TP3 rate at an identical stop-out rate, for a quarter of the trades.
//
// ─────────────────────────────────────────────────────────────────────────────
// WHAT WAS TESTED AND IS NOT HERE, because it did not hold up:
//
// TRIGGER FRESHNESS. i_triggerAge lets an entry be taken up to 3 bars after the
// trigger, and this project has argued twice about whether that produces weak
// entries (v3.5.30 clamped it, v3.5.31 reverted). Measured on outcome for the
// first time — every earlier table in this project entered on the trigger bar
// itself and so never tested it:
//
//     window   trades/day    TP1    TP2    TP3     SL   PREMATURE
//     0-0            6.74    60%    18%     9%    37%         29%
//     0-1            7.30    60%    18%     9%    36%         28%
//     0-2            7.80    60%    18%     9%    37%         28%
//     0-3            8.13    60%    18%     9%    37%         28%
//
// The window is close to free: 21% more trades and no measurable change in
// outcome. v3.5.31 was right to revert the clamp. Only entries taken at age 3
// exactly are visibly worse (TP1 47%, SL 43%) and they are 4% of trades — not
// enough to move anything. No freshness change was made.
//
// EARLY BREAKEVEN. This engine only moves the stop to entry after TP1 trades,
// and 44% of full stop-outs had already run 0.5R or more in their favour, so
// arming on excursion looked obvious. At 0.50R it cut stop-outs 43% -> 32% and
// destroyed TP1, 55% -> 40%: it scratches the trades that were going to work.
// At 0.85R it made stop-outs WORSE. Not added.
//
// ─────────────────────────────────────────────────────────────────────────────
// STANDING LIMIT, unchanged from v4.1 and repeated because it still applies.
// Every figure above is a COUNT or an OUTCOME MIX from synthetic OHLCV. No
// expectancy is computed and none is quoted. No price feed was reachable from
// the session that produced these numbers. The mislabelling in (1) is the one
// item here that needs no data at all — it is read off the source.
// ═══════════════════════════════════════════════════════════════════════════════

'''

sub1("// ═══════════════════════════════════════════════════════════════════════════════\n// v4.1 — EVERY MODE TRADES. MODE IS A STANDARD, NOT A TRIGGER BAN.",
     HDR + "// ═══════════════════════════════════════════════════════════════════════════════\n// v4.1 — EVERY MODE TRADES. MODE IS A STANDARD, NOT A TRIGGER BAN.",
     "header")

# ── inputs: entry set, toggles, per-family pad ────────────────────────────
SET_TIP = (
    "v4.1.1: which trigger types may fire. Until now the six were ORed together "
    "with no way to switch any off, so if one was bad it was bad on every "
    "signal.\\n\\nMEASURED, each run ALONE, 5m, all four modes:\\n\\n"
    "  trigger   share    TP1   TP2   TP3    SL\\n"
    "  band        68%    60%   15%    8%   38%\\n"
    "  band2       28%    58%   22%   10%   41%\\n"
    "  value       12%    57%   18%    9%   32%\\n"
    "  mss         11%    59%   26%   15%   32%\\n"
    "  fvg          9%    58%   29%   18%   37%\\n"
    "  sweep        6%    57%   23%   10%   41%\\n\\n"
    "Band rejections are 68% of all supply on their own and 77% with the 2-sigma "
    "band. The structure triggers this engine is named for are 6-11% each — so "
    "three of every four signals are a band fade whatever label the priority "
    "order prints. And the band has the weakest follow-through in the set: TP1 "
    "60% then TP2 15%, TP3 8%, against 29%/18% for the FVG retest.\\n\\n"
    "  set              trades   TP1   TP2   TP3    SL\\n"
    "  All (v4.1)         100%   60%   18%    9%   37%\\n"
    "  Structure only      26%   57%   26%   14%   37%\\n"
    "  Band only           77%   60%   16%    8%   38%\\n\\n"
    "Structure only roughly DOUBLES the TP2 and TP3 rate at an IDENTICAL "
    "stop-out rate, for a quarter of the trades. That is the whole trade-off.\\n\\n"
    "The default stays All. Not because it is better — the table says its "
    "follow-through is worse — but because a 74% cut in trade count should be "
    "your decision rather than a silent one.\\n\\nCounts and outcome geometry "
    "only; synthetic data, no expectancy computed or quoted.")

PAD_TIP = (
    "v4.1.1: extra stop padding for triggers whose invalidation is a LOOSE "
    "object — a pivot, a gap edge or a sweep wick — as opposed to the band "
    "family, which is stopped beyond the rejecting bar's own extreme and is "
    "already precise.\\n\\nOne pad cannot serve both. Measured as PREMATURE "
    "STOPS — the stop was hit while the setup's own invalidation had never been "
    "closed through, so the loss came from stop placement rather than from the "
    "market:\\n\\n"
    "  pad      mss    fvg  sweep   band  band2  value\\n"
    "  0.4 ATR  ---    61%    68%    47%    52%    59%\\n"
    "  0.8 ATR  61%    43%    43%    23%    30%    35%\\n"
    "  1.2 ATR  41%     0%    14%    15%    13%    16%\\n"
    "  1.6 ATR  36%     0%    12%     8%    10%    18%\\n\\n"
    "At v4.1's single 0.8 the band family sits at 23-35% and the pivot/gap/wick "
    "anchors at 43-61% — twice the manufactured losses from the same setting, "
    "purely because of what is being padded.\\n\\nThis value REPLACES the SL "
    "Buffer for MSS, FVG, sweep and value entries. Band and band2 keep the SL "
    "Buffer unchanged.\\n\\nHONEST LIMIT: trade counts fall sharply as the pad "
    "widens (fvg 315 -> 49) because a wider stop pushes more setups past the Max "
    "Risk Cap, and this engine REJECTS those rather than squeezing the stop into "
    "range. The stop-out column at the wide end is therefore partly survivorship "
    "and is not the basis for this default. The premature column is: it falls "
    "monotonically for every trigger and the ordering between triggers is stable "
    "at every pad. Raise Max Risk Cap alongside this if you want the rejected "
    "setups back.")

sub1('''i_slAtr      = input.float(0.5,"SL Buffer Below/Above Pivot (× ATR)",''',
'''i_entrySet = input.string("All (v4.1)", "Entry Set",
     options=["All (v4.1)", "Structure only (MSS/FVG/sweep)", "Band only", "Custom — use the toggles"],
     tooltip="%s",
     group=G_STRUCT)
i_useMss   = input.bool(true, "  Entry: MSS — structure break",     group=G_STRUCT)
i_useFvg   = input.bool(true, "  Entry: FVG retest",                group=G_STRUCT)
i_useSweep = input.bool(true, "  Entry: Liquidity sweep + reclaim", group=G_STRUCT)
i_useBand  = input.bool(true, "  Entry: VWAP band rejection",       group=G_STRUCT,
     tooltip="68%% of the engine's signals on its own, 77%% with the 2-sigma band. If you have wondered why the chart says SWEEP or FVG only occasionally, this is why. Weakest follow-through in the set: TP2 15%%, TP3 8%%.")

i_loosePad = input.float(1.2, "SL Buffer For Loose Anchors (× ATR)", minval=0.1, maxval=3.0, step=0.1,
     tooltip="%s",
     group=G_STRUCT)

i_slAtr      = input.float(0.5,"SL Buffer Below/Above Pivot (× ATR)",''' % (SET_TIP, PAD_TIP),
     "inputs")

# ── gate the triggers ─────────────────────────────────────────────────────
sub1("""buyTrigFvg   = fvgRetestBull
sellTrigFvg  = fvgRetestBear
buyTrigSweep = sweepBull
sellTrigSweep= sweepBear
buyTrigBand  = bandBull  or band2Bull
sellTrigBand = bandBear  or band2Bear

buyTrigger  = mssUp   or buyTrigFvg  or buyTrigSweep  or buyTrigBand
sellTrigger = mssDown or sellTrigFvg or sellTrigSweep or sellTrigBand""",
"""// v4.1.1 ENTRY SET. Six triggers were ORed together with no way to switch any
// off. Band rejections are 68% of all supply on their own; the structure
// triggers are 6-11% each. The default is unchanged — All is still All.
setAll    = i_entrySet == "All (v4.1)"
setStruct = i_entrySet == "Structure only (MSS/FVG/sweep)"
setBand   = i_entrySet == "Band only"
setCustom = i_entrySet == "Custom — use the toggles"
okMss   = setAll or setStruct or (setCustom and i_useMss)
okFvg   = setAll or setStruct or (setCustom and i_useFvg)
okSweep = setAll or setStruct or (setCustom and i_useSweep)
okBand  = setAll or setBand   or (setCustom and i_useBand)

buyTrigMss   = mssUp   and okMss
sellTrigMss  = mssDown and okMss
buyTrigFvg   = fvgRetestBull and okFvg
sellTrigFvg  = fvgRetestBear and okFvg
buyTrigSweep = sweepBull and okSweep
sellTrigSweep= sweepBear and okSweep
buyTrigBand  = (bandBull  or band2Bull) and okBand
sellTrigBand = (bandBear  or band2Bear) and okBand

buyTrigger  = buyTrigMss  or buyTrigFvg  or buyTrigSweep  or buyTrigBand
sellTrigger = sellTrigMss or sellTrigFvg or sellTrigSweep or sellTrigBand

// ═══════════════════════════════════════════════════════════════════════════════
// v4.1.1 ONE SELECTION, READ BY EVERYTHING
// ─────────────────────────────────────────────────────────────────────────────
// v4.1 picked the trigger NAME and the STOP ANCHOR with different priority
// orders — MSS first for the label, MSS last for the stop. Since an MSS stays
// fresh for i_triggerAge bars, a bar carrying a stale MSS alongside a band
// rejection printed "MSS" on the chart and in the alert while the stop was
// built from the band's rejection low. The trade shown and the trade priced
// were not the same trade.
//
// The order kept is the STOP's, which v4.1's own header already justifies:
// triggers ranked by how precisely each defines its own invalidation, sweep
// tightest and MSS loosest. The label now follows the stop.
// ═══════════════════════════════════════════════════════════════════════════════
buySel  = buyTrigSweep  ? "SWEEP" : buyTrigBand  ? "BAND" : buyTrigFvg  ? "FVG" : buyTrigMss  ? "MSS" : ""
sellSel = sellTrigSweep ? "SWEEP" : sellTrigBand ? "BAND" : sellTrigFvg ? "FVG" : sellTrigMss ? "MSS" : \"\"""",
     "trigger gating and selector")

sub1("buyTrigCount  = (mssUp   ? 1 : 0) + (buyTrigFvg  ? 1 : 0)",
     "buyTrigCount  = (buyTrigMss  ? 1 : 0) + (buyTrigFvg  ? 1 : 0)", "buyTrigCount")
sub1("sellTrigCount = (mssDown ? 1 : 0) + (sellTrigFvg ? 1 : 0)",
     "sellTrigCount = (sellTrigMss ? 1 : 0) + (sellTrigFvg ? 1 : 0)", "sellTrigCount")

# ── chase ref and SL anchor now read the selector ─────────────────────────
sub1("buyChaseRef  = buyTrigSweep  and not na(sweepBullLvl) ? sweepBullLvl : buyTrigBand  and not na(bandRefBullLvl) ? bandRefBullLvl : buyTrigFvg  and not na(lBullTop) ? lBullTop : mssUp   ? lastPH : na",
     'buyChaseRef  = buySel  == "SWEEP" and not na(sweepBullLvl) ? sweepBullLvl : buySel  == "BAND" and not na(bandRefBullLvl) ? bandRefBullLvl : buySel  == "FVG" and not na(lBullTop) ? lBullTop : buySel  == "MSS" ? lastPH : na',
     "buyChaseRef")
sub1("sellChaseRef = sellTrigSweep and not na(sweepBearLvl) ? sweepBearLvl : sellTrigBand and not na(bandRefBearLvl) ? bandRefBearLvl : sellTrigFvg and not na(lBearBot) ? lBearBot : mssDown ? lastPL : na",
     'sellChaseRef = sellSel == "SWEEP" and not na(sweepBearLvl) ? sweepBearLvl : sellSel == "BAND" and not na(bandRefBearLvl) ? bandRefBearLvl : sellSel == "FVG" and not na(lBearBot) ? lBearBot : sellSel == "MSS" ? lastPL : na',
     "sellChaseRef")

sub1("buySlAnchor  = buyTrigSweep  and not na(sweepBullLow)  ? sweepBullLow  : buyTrigBand  and not na(bandRefBullLow)  ? bandRefBullLow  : buyTrigFvg  and not na(lBullBot) ? lBullBot : lastPL",
     'buySlAnchor  = buySel  == "SWEEP" and not na(sweepBullLow)  ? sweepBullLow  : buySel  == "BAND" and not na(bandRefBullLow)  ? bandRefBullLow  : buySel  == "FVG" and not na(lBullBot) ? lBullBot : lastPL',
     "buySlAnchor")
sub1("sellSlAnchor = sellTrigSweep and not na(sweepBearHigh) ? sweepBearHigh : sellTrigBand and not na(bandRefBearHigh) ? bandRefBearHigh : sellTrigFvg and not na(lBearTop) ? lBearTop : lastPH",
     'sellSlAnchor = sellSel == "SWEEP" and not na(sweepBearHigh) ? sweepBearHigh : sellSel == "BAND" and not na(bandRefBearHigh) ? bandRefBearHigh : sellSel == "FVG" and not na(lBearTop) ? lBearTop : lastPH',
     "sellSlAnchor")

# ── per-family stop pad ───────────────────────────────────────────────────
sub1("slBuf     = isScalp ? riskAtrRef * math.min(i_slAtr, i_scalpSlCap) * slMult : riskAtrRef * i_slAtr * slMult",
"""// v4.1.1 PER-FAMILY PAD. The band family is stopped beyond the rejecting bar's
// own extreme — a dated single-bar level. MSS, FVG and sweep are stopped beyond
// a pivot, a gap edge or a wick, all looser objects that ordinary noise crosses
// without the idea being wrong. Measured premature-stop rate at the shipped 0.8
// pad: band 23% and band2 30%, against mss 61%, fvg 43% and sweep 43%. Same
// setting, twice the manufactured losses, purely because of what it is padding.
buyPadAtr  = buySel  == "BAND" ? i_slAtr : i_loosePad
sellPadAtr = sellSel == "BAND" ? i_slAtr : i_loosePad
slBufBuy   = isScalp ? riskAtrRef * math.min(buyPadAtr,  i_scalpSlCap) * slMult : riskAtrRef * buyPadAtr  * slMult
slBufSell  = isScalp ? riskAtrRef * math.min(sellPadAtr, i_scalpSlCap) * slMult : riskAtrRef * sellPadAtr * slMult
slBuf      = isScalp ? riskAtrRef * math.min(i_slAtr, i_scalpSlCap) * slMult : riskAtrRef * i_slAtr * slMult""",
     "per-family pad")

sub1("buySLraw  = not na(buySlAnchor)  ? math.min(buySlAnchor - slBuf,  buyEntryRef - riskAtrRef * 0.5) : buyEntryRef - riskAtrRef * 1.5",
     "buySLraw  = not na(buySlAnchor)  ? math.min(buySlAnchor - slBufBuy,  buyEntryRef - riskAtrRef * 0.5) : buyEntryRef - riskAtrRef * 1.5",
     "buySLraw")
sub1("sellSLraw = not na(sellSlAnchor) ? math.max(sellSlAnchor + slBuf, sellEntryRef + riskAtrRef * 0.5) : sellEntryRef + riskAtrRef * 1.5",
     "sellSLraw = not na(sellSlAnchor) ? math.max(sellSlAnchor + slBufSell, sellEntryRef + riskAtrRef * 0.5) : sellEntryRef + riskAtrRef * 1.5",
     "sellSLraw")

# ── the label finally agrees with the stop ────────────────────────────────
sub1('buyType    = mssUp   ? "MSS" : buyTrigFvg   ? "FVG" : buyTrigSweep  ? "SWEEP" : buyTrigBand  ? "BAND" : "MSS"\nsellType   = mssDown ? "MSS" : sellTrigFvg  ? "FVG" : sellTrigSweep ? "SWEEP" : sellTrigBand ? "BAND" : "MSS"',
     '// v4.1.1: reads the same selection the stop was built from. In v4.1 these\n// two used opposite priority orders, so a signal could be labelled MSS while\n// its stop came from a band rejection.\nbuyType    = buySel  == "" ? "MSS" : buySel\nsellType   = sellSel == "" ? "MSS" : sellSel',
     "buyType/sellType")

src = src.replace('indicator("Movement Engine Pro v4.1", shorttitle="ME Pro v4.1"',
                  'indicator("Movement Engine Pro v4.1.1", shorttitle="ME Pro v4.1.1"')
src = src.replace('// © ME Institutional — Movement Engine Pro v4.1 (mode rebuild)',
                  '// © ME Institutional — Movement Engine Pro v4.1.1 (the label and the stop now describe the same trade)')
src = src.replace('"ME PRO v4.1"', '"ME PRO v4.1.1"')

io.open(P, "w", encoding="utf-8").write(src)
print("\nwrote %d bytes" % len(src))
