"""MEScalp EA v2.3 — the TP1 counter, ported from the Pine finding."""
import io, sys, shutil

SRC = "/home/user/Claude/MEScalp_v22.mq5"
P = "/home/user/Claude/MEScalp_v23.mq5"
shutil.copy(SRC, P)
src = io.open(P, encoding="utf-8").read()


def sub1(old, new, tag):
    global src
    if src.count(old) != 1:
        sys.exit("PATCH %s: expected 1, found %d" % (tag, src.count(old)))
    src = src.replace(old, new)
    print("  ok  %s" % tag)


# ── header ────────────────────────────────────────────────────────────────
sub1("""//  THIS FILE HAS NOT BEEN COMPILED. No MQL5 toolchain was available in the
//  environment that wrote it. Expect to fix compile errors on first open in
//  MetaEditor; the logic is what took the work, not the syntax.""",
"""//  v2.3 — TP1 IS NOW COUNTED, AND THE TWO STOP PADS ARE DECLARED.
//
//  1. TP1 REACH IS MEASURED ON YOUR ACCOUNT, NOT MINE.
//     The Pine version could not say TP1 had been hit: a plan that reached it
//     and returned to entry was stamped "BE", which reads as a miss but is the
//     only outcome that PROVES TP1 filled. Apparent reach 19%, real reach 59%
//     on 5m.
//     The EA has the same blind spot with a worse consequence — an unfilled
//     TP1 leg leaves the whole position carrying full risk, and nothing in the
//     terminal tells you how often that happens.
//     Now: every TP1 fill is printed to the Experts log with the running rate,
//     and the panel carries "TP1 reach  N%  (hit/taken)". That is a live count
//     on your symbol and your broker, which outranks anything my generator
//     produced.
//
//     Measured reach for reference (BE + TP3, synthetic):
//       TP1 xATR    5m     15m          TP1 xATR    5m     15m
//       0.40       77%     61%          0.80       59%     48%   <- default
//       0.50       72%     57%          1.00       52%     42%
//
//  2. TWO STOP PADS STACK, AND NEITHER INPUT SAID SO.
//       stop = min(invalidation, close -/+ atr*InpMinRisk)
//              -/+ atr*InpSlBuf -/+ atr*InpStructPad
//     InpSlBuf (0.20) and InpStructPad (0.25) do the same job and ADD. The
//     clearance actually applied has always been 0.45 ATR. The panel now shows
//     the effective total so it cannot stay hidden.
//
//     Sweeping the buffer, pad held at 0.25 (synthetic):
//       buf   total   5m trd/day   5m SL   15m SL
//       0.00   0.25         5.43     17%      29%
//       0.20   0.45         5.43     13%      24%
//       0.50   0.75         5.43      9%      20%
//
//     Trade count does NOT change — I expected the wider stop to be rejected
//     by the Structure Backstop and it is not. That guess was wrong.
//     The cost the table cannot show: position size divides by stop distance,
//     so a wider stop means a smaller position for the same money at risk
//     while targets stay at fixed ATR distances. Fewer stop-outs, smaller
//     wins. Defaults unchanged, because outcome mix cannot settle that and
//     expectancy has not been measured.
//
//  THIS FILE HAS NOT BEEN COMPILED. No MQL5 toolchain was available in the
//  environment that wrote it. Expect to fix compile errors on first open in
//  MetaEditor; the logic is what took the work, not the syntax.""",
     "header")

src = src.replace('#property version   "2.20"', '#property version   "2.30"')
src = src.replace("//|                                                  MEScalp_v22.mq5 |",
                  "//|                                                  MEScalp_v23.mq5 |")
src = src.replace("//|                    © ME Institutional — ME Scalp v2.2 for MT5    |",
                  "//|                    © ME Institutional — ME Scalp v2.3 for MT5    |")

# ── counters ──────────────────────────────────────────────────────────────
sub1("double   gSpreadShare = 0.0;",
"""double   gSpreadShare = 0.0;
// v2.3 TP1 REACH, counted live. gTaken counts plans opened, gTp1Hit counts
// those that reached TP1. The ratio is the reach rate for THIS symbol, THIS
// broker and THIS session, which is worth more than any figure from a
// synthetic generator.
int      gTaken   = 0;
int      gTp1Hit  = 0;""",
     "counters")

# ── count on entry ────────────────────────────────────────────────────────
sub1("""   planTag     = tag;
   lastSignalBar  = planOpenBar;
   barsSinceEntry = 0;""",
"""   planTag     = tag;
   lastSignalBar  = planOpenBar;
   barsSinceEntry = 0;
   gTaken++;""",
     "count taken")

# ── count and log on TP1 ──────────────────────────────────────────────────
sub1("""      planTp1Done = true;
      if(vol - minL >= minL) trade.PositionClosePartial(pos.Ticket(), NormaliseLots(vol / 3.0));""",
"""      planTp1Done = true;
      // v2.3: say it out loud. An unfilled TP1 leg means the position is still
      // carrying full risk, and through v2.2 nothing in the terminal reported
      // how often that was happening.
      gTp1Hit++;
      PrintFormat("ME Scalp TP1 hit @ %.*f | %s %s | TP1 reach %d/%d = %.0f%%",
                  _Digits, px, planIsBuy ? "LONG" : "SHORT", planTag,
                  gTp1Hit, gTaken, gTaken > 0 ? 100.0 * gTp1Hit / gTaken : 0.0);
      if(vol - minL >= minL) trade.PositionClosePartial(pos.Ticket(), NormaliseLots(vol / 3.0));""",
     "count tp1")

# ── panel: reach rate and the effective pad ───────────────────────────────
sub1('''      "spread   %d pt  =  %.0f%% of stop (cap %.0f%%)\\n"
      "trade    %s\\n"
      "last     %s",''',
'''      "spread   %d pt  =  %.0f%% of stop (cap %.0f%%)\\n"
      "TP1      reach %s   |  stop pad %.2f ATR\\n"
      "trade    %s\\n"
      "last     %s",''',
     "panel format")

sub1("""      (int)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD), gSpreadShare, InpMaxSpreadPctRisk,
      st, gLastBlock));""",
"""      (int)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD), gSpreadShare, InpMaxSpreadPctRisk,
      gTaken > 0 ? StringFormat("%.0f%%  (%d/%d)", 100.0 * gTp1Hit / gTaken, gTp1Hit, gTaken)
                 : "no trades yet",
      InpSlBuf + InpStructPad,
      st, gLastBlock));""",
     "panel args")

# ── the stacking, declared where the inputs are ───────────────────────────
sub1('input double          InpStructPad   = 0.25;           // Structure pad beyond invalidation (xATR)',
     'input double          InpStructPad   = 0.25;           // Structure pad beyond invalidation (xATR) - ADDS TO InpSlBuf',
     "structpad label")
src = src.replace('input double          InpSlBuf       = 0.20;           // SL buffer past invalidation (xATR)',
                  'input double          InpSlBuf       = 0.20;           // SL buffer past invalidation (xATR) - ADDS TO InpStructPad; total shown on panel')

io.open(P, "w", encoding="utf-8").write(src)
print("\nwrote %d bytes" % len(src))
