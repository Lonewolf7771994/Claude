"""ME Pro v5.2 — you can finally turn an entry type off, and see which one fires."""
import io, sys, shutil

SRC = "/home/user/Claude/MovementEnginePro.v5.1.pine"
P = "/home/user/Claude/MovementEnginePro.v5.2.pine"
shutil.copy(SRC, P)
src = io.open(P, encoding="utf-8").read()


def sub1(old, new, tag):
    global src
    if src.count(old) != 1:
        sys.exit("PATCH %s: expected 1, found %d" % (tag, src.count(old)))
    src = src.replace(old, new)
    print("  ok  %s" % tag)


SET_TIP = (
    "WHICH ENTRIES ACTUALLY FIRE, AND WHAT THEY ARE WORTH. Until v5.2 the six "
    "trigger types were ORed together with no way to switch any of them off, so "
    "if one was bad it was bad on every signal and no setting helped.\\n\\n"
    "Each was then run ALONE — the engine with exactly one trigger enabled, "
    "which is what these toggles do, so the table predicts what you get rather "
    "than describing an attribution.\\n\\nMEASURED, 5m, Rapid pace, all four "
    "modes, 3 seeds, 0.8 ATR stop buffer:\\n\\n"
    "  trigger    trades  share   TP1   TP2   TP3    BE    SL  bars  PREM\\n"
    "  ALL (v5.1)   2425   100%   60%   18%    9%   50%   37%     8   29%\\n"
    "  mss           268    11%   59%   26%   15%   43%   32%    17   49%\\n"
    "  fvg           221     9%   58%   29%   18%   39%   37%     4   43%\\n"
    "  sweep         157     6%   57%   23%   10%   45%   41%     7   42%\\n"
    "  band         1654    68%   60%   15%    8%   52%   38%     9   24%\\n"
    "  band2         673    28%   58%   22%   10%   48%   41%    11   26%\\n"
    "  value         292    12%   57%   18%    9%   46%   32%     5   31%\\n\\n"
    "READ THE SHARE COLUMN FIRST. VWAP band rejections are 68% of everything "
    "the engine produces, and band plus band2 together are 77%. The ICT "
    "structure triggers this indicator is named for — MSS, FVG, sweep — are "
    "6-11% each. THREE OUT OF FOUR SIGNALS ARE A VWAP BAND FADE wearing "
    "whichever label the priority order happened to print. That is the precise "
    "sense in which the entries were misleading, and it is a supply fact, not "
    "an opinion.\\n\\nAND THE BAND IS THE WEAKEST FOLLOW-THROUGH IN THE SET. It "
    "reaches TP1 as often as anything (60%) and then stops: TP2 15%, TP3 8%, "
    "against 26%/15% for MSS and 29%/18% for FVG. A trade that hits its first "
    "target and dies is exactly what 'looks like it works but does not' means.\\n\\n"
    "THE SETS:\\n\\n"
    "  set              trades  share   TP1   TP2   TP3    SL  bars  PREM\\n"
    "  All (v5.1)         2425   100%   60%   18%    9%   37%     8   29%\\n"
    "  Structure only      642    26%   57%   26%   14%   37%     8   46%\\n"
    "  Band only          1865    77%   60%   16%    8%   38%     8   23%\\n\\n"
    "Structure only gives you roughly DOUBLE the TP2 and TP3 rate at an "
    "IDENTICAL stop-out rate — and a quarter of the trades. That is the whole "
    "trade-off in one line. It also carries a higher premature-stop rate (46% "
    "against 29%), because a pivot or a gap edge is a looser invalidation than "
    "a deviation band; raise the SL Buffer further if you run it.\\n\\n"
    "WHY 'All' IS STILL THE DEFAULT. Structure only fires about 0.9/day on 5m "
    "Aggressive against 3.6, and this engine has already been silent once. The "
    "default is not a claim that All is better — the table above says the "
    "follow-through is worse. It is a claim that changing your trade count by "
    "74% is your decision, not a silent one.\\n\\nThe POC reclaim and CRT "
    "triggers are NOT in the table. This harness does not implement them, so "
    "nothing is measured about them and nothing is claimed; their toggles are "
    "provided so you can isolate them yourself on a real chart.\\n\\nCounts and "
    "outcome geometry only. No expectancy computed or quoted; synthetic data.")

# ── the Entry Set control and the six toggles ──────────────────────────────
sub1("""i_slAtr      = input.float(0.8,"SL Buffer Below/Above Pivot (× ATR)",""",
"""i_entrySet = input.string("All (v5.1)", "Entry Set",
     options=["All (v5.1)", "Structure only (MSS/FVG/sweep)", "Band only", "Custom — use the toggles"],
     tooltip="%s",
     group=G_STRUCT)
i_useMss   = input.bool(true,  "  Entry: MSS — structure break",      group=G_STRUCT)
i_useFvg   = input.bool(true,  "  Entry: FVG retest",                 group=G_STRUCT)
i_useSweep = input.bool(true,  "  Entry: Liquidity sweep + reclaim",  group=G_STRUCT)
i_useBand  = input.bool(true,  "  Entry: VWAP band rejection",        group=G_STRUCT,
     tooltip="68%% of the engine's supply on its own, 77%% with the 2-sigma band. If you have ever wondered why the chart labels say SWEEP or FVG only occasionally, this is the answer. Weakest follow-through in the set: TP2 15%%, TP3 8%%.")
i_usePoc   = input.bool(true,  "  Entry: POC reclaim",                group=G_STRUCT,
     tooltip="Not implemented in the harness that produced the Entry Set table, so no measurement is quoted for it and none should be inferred.")
i_useCrt   = input.bool(true,  "  Entry: CRT candle range",           group=G_STRUCT,
     tooltip="Not implemented in the harness that produced the Entry Set table, so no measurement is quoted for it and none should be inferred.")

i_slAtr      = input.float(0.8,"SL Buffer Below/Above Pivot (× ATR)",""" % SET_TIP,
     "entry set inputs")

# ── resolve the preset into effective toggles, then gate every trigger ─────
sub1("""buyTrigFvg   = fvgRetestBull
sellTrigFvg  = fvgRetestBear
buyTrigSweep = sweepBull
sellTrigSweep= sweepBear
buyTrigBand  = bandBull  or band2Bull
sellTrigBand = bandBear  or band2Bear""",
"""// ═══════════════════════════════════════════════════════════════════════════════
// v5.2 ENTRY SET — the toggles that did not exist
// ─────────────────────────────────────────────────────────────────────────────
// Six trigger types were ORed together and none could be switched off. Measured
// one at a time, VWAP band rejections turned out to be 68% of all supply on
// their own and 77% with the 2-sigma band — so three of every four signals were
// a band fade regardless of which label the priority order printed on the
// chart. They also have the weakest follow-through in the set: TP1 60% and then
// TP2 15%, TP3 8%, against 29%/18% for the FVG retest.
//
// The full table is in the Entry Set tooltip. Nothing about the DEFAULT
// behaviour changes here — All is still All — but the composition is now both
// selectable and visible on the dashboard.
// ═══════════════════════════════════════════════════════════════════════════════
setAll    = i_entrySet == "All (v5.1)"
setStruct = i_entrySet == "Structure only (MSS/FVG/sweep)"
setBand   = i_entrySet == "Band only"
setCustom = i_entrySet == "Custom — use the toggles"
okMss   = setAll or setStruct or (setCustom and i_useMss)
okFvg   = setAll or setStruct or (setCustom and i_useFvg)
okSweep = setAll or setStruct or (setCustom and i_useSweep)
okBand  = setAll or setBand   or (setCustom and i_useBand)
okPoc   = setAll or (setCustom and i_usePoc)
okCrt   = setAll or (setCustom and i_useCrt)

buyTrigMss   = mssUp   and okMss
sellTrigMss  = mssDown and okMss
buyTrigFvg   = fvgRetestBull and okFvg
sellTrigFvg  = fvgRetestBear and okFvg
buyTrigSweep = sweepBull and okSweep
sellTrigSweep= sweepBear and okSweep
buyTrigBand  = (bandBull  or band2Bull) and okBand
sellTrigBand = (bandBear  or band2Bear) and okBand""",
     "trigger gating")

sub1("buyTrigPoc   = pocBull\nsellTrigPoc  = pocBear\nbuyTrigCrt   = crtBull\nsellTrigCrt  = crtBear",
     "buyTrigPoc   = pocBull and okPoc\nsellTrigPoc  = pocBear and okPoc\nbuyTrigCrt   = crtBull and okCrt\nsellTrigCrt  = crtBear and okCrt",
     "poc/crt gating")

sub1("buyTrigger  = mssUp   or buyTrigFvg  or buyTrigSweep  or buyTrigBand  or buyTrigPoc  or buyTrigCrt\nsellTrigger = mssDown or sellTrigFvg or sellTrigSweep or sellTrigBand or sellTrigPoc or sellTrigCrt",
     "buyTrigger  = buyTrigMss  or buyTrigFvg  or buyTrigSweep  or buyTrigBand  or buyTrigPoc  or buyTrigCrt\nsellTrigger = sellTrigMss or sellTrigFvg or sellTrigSweep or sellTrigBand or sellTrigPoc or sellTrigCrt",
     "trigger union")

sub1('buySel  = buyTrigCrt  ? "CRT" : buyTrigSweep  ? "SWEEP" : buyTrigBand  ? "BAND" : buyTrigFvg  ? "FVG" : buyTrigPoc  ? "POC" : mssUp   ? "MSS" : ""',
     'buySel  = buyTrigCrt  ? "CRT" : buyTrigSweep  ? "SWEEP" : buyTrigBand  ? "BAND" : buyTrigFvg  ? "FVG" : buyTrigPoc  ? "POC" : buyTrigMss  ? "MSS" : ""',
     "buySel")
sub1('sellSel = sellTrigCrt ? "CRT" : sellTrigSweep ? "SWEEP" : sellTrigBand ? "BAND" : sellTrigFvg ? "FVG" : sellTrigPoc ? "POC" : mssDown ? "MSS" : ""',
     'sellSel = sellTrigCrt ? "CRT" : sellTrigSweep ? "SWEEP" : sellTrigBand ? "BAND" : sellTrigFvg ? "FVG" : sellTrigPoc ? "POC" : sellTrigMss ? "MSS" : ""',
     "sellSel")

sub1("buyTrigCount  = (mssUp   ? 1 : 0) + (buyTrigFvg  ? 1 : 0)",
     "buyTrigCount  = (buyTrigMss  ? 1 : 0) + (buyTrigFvg  ? 1 : 0)", "buyTrigCount")
sub1("sellTrigCount = (mssDown ? 1 : 0) + (sellTrigFvg ? 1 : 0)",
     "sellTrigCount = (sellTrigMss ? 1 : 0) + (sellTrigFvg ? 1 : 0)", "sellTrigCount")

# ── live composition counters ─────────────────────────────────────────────
sub1("buySignal  = levelMode ? fireBuy  : qualBuy\nsellSignal = levelMode ? fireSell : qualSell",
"""buySignal  = levelMode ? fireBuy  : qualBuy
sellSignal = levelMode ? fireSell : qualSell

// v5.2 ENTRY MIX. The share table in the Entry Set tooltip was measured on
// synthetic data; this counts the same thing on the chart in front of you, so
// the claim that most signals are band fades is checkable rather than taken on
// trust. Counts only signals that actually fired.
var int mixMss = 0
var int mixFvg = 0
var int mixSwp = 0
var int mixBnd = 0
var int mixPoc = 0
var int mixCrt = 0
if barstate.isconfirmed and (buySignal or sellSignal)
    string mixSel = buySignal ? buySel : sellSel
    if mixSel == "MSS"
        mixMss := mixMss + 1
    else if mixSel == "FVG"
        mixFvg := mixFvg + 1
    else if mixSel == "SWEEP"
        mixSwp := mixSwp + 1
    else if mixSel == "BAND"
        mixBnd := mixBnd + 1
    else if mixSel == "POC"
        mixPoc := mixPoc + 1
    else if mixSel == "CRT"
        mixCrt := mixCrt + 1
mixTot = mixMss + mixFvg + mixSwp + mixBnd + mixPoc + mixCrt""",
     "entry mix counters")

# ── dashboard: append a row at the END so nothing above it shifts ──────────
sub1("dash := table.new(tPos, 3, 27, bgcolor=color.rgb(10, 10, 15, 10), border_width=1, border_color=color.rgb(40, 40, 50))",
     "dash := table.new(tPos, 3, 28, bgcolor=color.rgb(10, 10, 15, 10), border_width=1, border_color=color.rgb(40, 40, 50))",
     "table size")
sub1("        table.merge_cells(dash, 1, 26, 2, 26)",
     "        table.merge_cells(dash, 1, 26, 2, 26)\n        table.merge_cells(dash, 1, 27, 2, 27)",
     "merge row 27")

sub1('    table.cell(dash, 0, 26, "Last Block"',
'''    f_mixPct(int a) => mixTot > 0 ? str.tostring(math.round(100.0 * a / mixTot)) + "%" : "—"
    table.cell(dash, 0, 27, "Entry mix (" + str.tostring(mixTot) + ")", text_color=dim, text_size=size.tiny, text_halign=text.align_left, bgcolor=color.rgb(15, 15, 22))
    table.cell(dash, 1, 27, mixTot == 0 ? "no signals yet" : "BAND " + f_mixPct(mixBnd) + "  MSS " + f_mixPct(mixMss) + "  FVG " + f_mixPct(mixFvg) + "  SWP " + f_mixPct(mixSwp) + (mixPoc > 0 ? "  POC " + f_mixPct(mixPoc) : "") + (mixCrt > 0 ? "  CRT " + f_mixPct(mixCrt) : ""), text_color=mixTot == 0 ? dim : (mixBnd * 2 > mixTot ? yel : wht), text_size=size.tiny)
    table.cell(dash, 0, 26, "Last Block"''',
     "entry mix row")

src = src.replace('indicator("Movement Engine Pro v5.1", shorttitle="ME Pro v5.1"',
                  'indicator("Movement Engine Pro v5.2", shorttitle="ME Pro v5.2"')
src = src.replace('// © ME Institutional — Movement Engine Pro v5.1 (44% of the stop-outs were the stop, not the market)',
                  '// © ME Institutional — Movement Engine Pro v5.2 (three of four signals were a band fade)')
src = src.replace('"ME PRO v5.1"', '"ME PRO v5.2"')

io.open(P, "w", encoding="utf-8").write(src)
print("\nwrote %d bytes" % len(src))
