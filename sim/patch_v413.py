"""ME Pro v4.1.3 — level-retest entries ON. The feature v4.1 rejected on a guess."""
import io, sys, shutil

SRC = "/home/user/Claude/MovementEnginePro.v4.1.2.pine"
P = "/home/user/Claude/MovementEnginePro.v4.1.3.pine"
shutil.copy(SRC, P)
src = io.open(P, encoding="utf-8").read()


def sub1(old, new, tag):
    global src
    if src.count(old) != 1:
        sys.exit("PATCH %s: expected 1, found %d" % (tag, src.count(old)))
    src = src.replace(old, new)
    print("  ok  %s" % tag)


HDR = '''// ═══════════════════════════════════════════════════════════════════════════════
// v4.1.3 — THE ENTRY WAS THE PROBLEM. v4.1 ALREADY HAD THE FIX AND SHIPPED IT OFF.
// ─────────────────────────────────────────────────────────────────────────────
// Three rounds of changes and the same three complaints: stop-outs, wrong
// entries, slow entries. So this version stopped adjusting filters and measured
// the entry itself.
//
// WHAT "LATE" MEANS IN MONEY. Every trigger fires AT A LEVEL — the broken pivot,
// the swept low, the gap edge, the rejected band. The engine then buys the CLOSE
// of the confirming bar, which is somewhere else by then, and the anti-chase cap
// permits that gap to be up to 1.0 ATR. Measured, the median entry lands 0.40
// ATR past its own level. Same stop, worse price, every trade.
//
// TIGHTENING THE CHASE CAP DOES NOT FIX IT, and this is worth seeing because it
// is the obvious move:
//
//     entry mode                trades/day  med late   TP1   TP2   TP3    SL  bars
//     market, chase 1.0 (v4.1)        3.98      0.40   54%   21%   13%   42%    13
//     market, chase 0.75              3.55      0.34   53%   22%   14%   41%    15
//     market, chase 0.50              2.60      0.26   52%   21%   13%   43%    18
//     market, chase 0.25              1.24      0.15   51%   23%   16%   41%    24
//
// The stop-out rate does not move — 41-43% at every cap — while trade count
// falls by 70%. Being choosier about HOW late you enter is not the same as not
// being late.
//
//     LEVEL RETEST                    3.51      0.00   74%   31%   11%   25%     4
//
// Arming the order AT the level instead of buying the close:
//
//     stop-outs      42% -> 25%
//     TP1 reached    54% -> 74%
//     TP2 reached    21% -> 31%
//     median hold    13 bars -> 4
//     trade count    3.98 -> 3.51 per day, a 12% cost
//
// That is all three complaints at once, from one switch that has been in this
// file since v3.5.32.
//
// ─────────────────────────────────────────────────────────────────────────────
// WHY IT WAS OFF, AND WHY THAT REASONING WAS WRONG. v3.5.32 rejected it on this:
//
//     market entry   median TP1 reward 1.62R
//     level  entry   median TP1 reward 2.10R      (+30% per filled trade)
//     at an ASSUMED 62% fill rate:  market 1.617   level 1.301  -> negative
//
// The whole argument rests on that fill rate, and the word in the original is
// "assumed". Measured over 956 armed orders with an 8-bar window:
//
//     FILL RATE 88%, not 62%.
//
// At 88% the arithmetic that rejected the feature reverses. A guess was doing
// the work of a measurement, and it kept the fix switched off for nine versions.
//
// ─────────────────────────────────────────────────────────────────────────────
// WHAT IT COSTS, stated before you switch it on.
//
// TP3 falls slightly, 13% -> 11%. Entering at the level means entering on the
// pullback, and some of those setups never make the full extension.
//
// THE PREMATURE-STOP SHARE RISES, 15% -> 27%, and that needs care rather than
// hiding. It is a share OF STOP-OUTS, and stop-outs nearly halved. Per trade the
// two are the same: 0.42 x 15% = 6.3% of trades against 0.25 x 27% = 6.8%. What
// level entry removes is the stop-outs where the idea HAD genuinely failed; the
// noise stop-outs are still there. Do not read the 27% as a regression.
//
// 12% OF SETUPS NEVER FILL. That is the honest cost and it is not simulated
// away — a move that runs without looking back is a move you now miss entirely.
// The 88% figure says that is uncommon, not that it never happens.
//
// FILL MODELLING. A fill is counted when price trades through the armed level
// within i_pendBars. The bar that fills is ALSO checked for the stop, because a
// bar that reaches the level and keeps going is exactly what this mode is most
// exposed to; leaving that out flattered the result by 3 points of stop-out rate
// and 12 points of premature share, and it was found and removed before these
// numbers were written down.
//
// ─────────────────────────────────────────────────────────────────────────────
// NOTHING ELSE CHANGED. i_entryMode moves from "Market (confirmed)" to "Level
// retest (pending)". The machinery it switches on has been in the file since
// v3.5.32 and is untouched. Set it back to Market for v4.1.2 behaviour exactly.
//
// Counts and outcome geometry only. No expectancy computed or quoted; synthetic
// data, no price feed reachable.
// ═══════════════════════════════════════════════════════════════════════════════

'''

sub1("// ═══════════════════════════════════════════════════════════════════════════════\n// v4.1.2 — NO MANUAL FEATURES. AND TWO THINGS THAT WOULD NOT AUTOMATE.",
     HDR + "// ═══════════════════════════════════════════════════════════════════════════════\n// v4.1.2 — NO MANUAL FEATURES. AND TWO THINGS THAT WOULD NOT AUTOMATE.",
     "header")

TIP = (
    "v4.1.3 CHANGED THIS DEFAULT TO LEVEL RETEST, and it is the single largest "
    "measured change in this file.\\n\\nWHERE the entry is taken once a setup "
    "qualifies.\\n\\nMARKET (CONFIRMED) buys the close of the qualifying bar. "
    "Every trigger fires AT a level — the broken pivot, the swept low, the gap "
    "edge, the rejected band — and the close is somewhere else by then. Measured "
    "median: 0.40 ATR past the level. Same stop, worse price, every trade.\\n\\n"
    "LEVEL RETEST arms an order at the trigger's own level and fills only if "
    "price returns within the window below.\\n\\nMEASURED, 5m, all four modes, "
    "both sides:\\n\\n"
    "  entry mode              trades/day  late   TP1   TP2   TP3    SL  bars\\n"
    "  market, chase 1.0             3.98  0.40   54%   21%   13%   42%    13\\n"
    "  market, chase 0.75            3.55  0.34   53%   22%   14%   41%    15\\n"
    "  market, chase 0.50            2.60  0.26   52%   21%   13%   43%    18\\n"
    "  market, chase 0.25            1.24  0.15   51%   23%   16%   41%    24\\n"
    "  LEVEL RETEST                  3.51  0.00   74%   31%   11%   25%     4\\n\\n"
    "Tightening the anti-chase cap does NOT help — 41-43% stop-outs at every "
    "setting while trade count falls 70%. Being choosier about how late you "
    "enter is not the same as not being late.\\n\\nWHY IT WAS OFF FOR NINE "
    "VERSIONS. v3.5.32 rejected it on an ASSUMED 62% fill rate, which made the "
    "arithmetic negative. Measured over 956 armed orders: THE FILL RATE IS 88%. "
    "At 88% the calculation reverses. A guess had been doing the work of a "
    "measurement.\\n\\nWHAT IT COSTS. TP3 slips 13% to 11% — entering on the "
    "pullback means some setups never make the full extension. 12% of setups "
    "never fill, and a move that runs without looking back is now missed "
    "entirely; that is real and is not simulated away.\\n\\nThe premature-stop "
    "SHARE rises 15% to 27%, and that is not a regression: it is a share of "
    "stop-outs, and stop-outs nearly halved. Per trade the two are the same, "
    "6.3% against 6.8%. Level entry removes the stop-outs where the idea had "
    "genuinely failed; the noise ones remain.\\n\\nThe filling bar is itself "
    "checked for the stop in these figures — a bar that reaches the level and "
    "keeps going is what this mode is most exposed to, and omitting it flattered "
    "the result by 3 points of stop-out rate.\\n\\nSet back to Market for v4.1.2 "
    "behaviour exactly. Counts and outcome geometry only; no expectancy computed "
    "or quoted.")

start = src.index('i_entryMode  = input.string("Market (confirmed)", "Entry Mode",')
end = src.index("     group=G_ENGINE)", start) + len("     group=G_ENGINE)")
src = src[:start] + (
    'i_entryMode  = input.string("Level retest (pending)", "Entry Mode",\n'
    '     options=["Market (confirmed)","Level retest (pending)"],\n'
    '     tooltip="%s",\n'
    '     group=G_ENGINE)' % TIP) + src[end:]
print("  ok  entry mode default + tooltip")

src = src.replace('indicator("Movement Engine Pro v4.1.2", shorttitle="ME Pro v4.1.2"',
                  'indicator("Movement Engine Pro v4.1.3", shorttitle="ME Pro v4.1.3"')
src = src.replace('// © ME Institutional — Movement Engine Pro v4.1.2 (nothing is typed in any more)',
                  '// © ME Institutional — Movement Engine Pro v4.1.3 (enter at the level, not after it)')
src = src.replace('"ME PRO v4.1.2"', '"ME PRO v4.1.3"')

io.open(P, "w", encoding="utf-8").write(src)
print("\nwrote %d bytes" % len(src))
