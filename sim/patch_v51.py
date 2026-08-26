"""ME Pro v5.1 — the stop buffer, after 44% of stop-outs were shown premature."""
import io, sys, shutil

SRC = "/home/user/Claude/MovementEnginePro.v5.0.pine"
P = "/home/user/Claude/MovementEnginePro.v5.1.pine"
shutil.copy(SRC, P)
src = io.open(P, encoding="utf-8").read()


def sub1(old, new, tag):
    global src
    if src.count(old) != 1:
        sys.exit("PATCH %s: expected 1, found %d" % (tag, src.count(old)))
    src = src.replace(old, new)
    print("  ok  %s" % tag)


TIP = (
    "v5.1 CHANGED THIS DEFAULT FROM 0.5 TO 0.8, and it is the largest single "
    "change to outcome in the file.\\n\\nWHY. A report of trades stopped out "
    "that then went on to work is testable, so it was tested. For every full "
    "stop-out the harness asked whether the setup's OWN invalidation level had "
    "ever been closed through before the stop was hit. If it had not, the "
    "trade was closed while its thesis was still intact — the loss came from "
    "where the stop was, not from the market.\\n\\nMEASURED, 5m, Rapid pace, "
    "all four modes, 3 seeds, structural stop, ATR ladder:\\n\\n"
    "  buffer   trades   med R    TP1    TP2     BE     SL   bars   PREMATURE\\n"
    "  0.5 ATR    3806    1.34    55%    17%    47%    43%      5         44%\\n"
    "  0.8 ATR    2425    1.52    60%    18%    50%    37%      8         29%\\n"
    "  1.2 ATR    1421    2.01    55%    21%    42%    40%     13         14%\\n"
    "  1.6 ATR    1122    2.37    60%    24%    48%    34%     18          6%\\n"
    "  2.0 ATR     665    2.60    65%    28%    52%    28%     33          0%\\n\\n"
    "At the old 0.5 default, NEARLY HALF of all full stop-outs happened without "
    "the level that defines the trade ever being broken. 0.8 takes that to 29% "
    "and improves the stop-out rate, the TP1 rate and the breakeven rate at the "
    "same time — the only row in the table that improves everything at once.\\n\\n"
    "THE COST, WHICH IS NOT ONLY HOLD TIME. Trade count falls 3806 -> 2425, "
    "about a third. A wider stop pushes more setups past the Max Risk Cap, and "
    "this engine REJECTS those rather than squeezing the stop into range — "
    "squeezing produces a stop that no longer marks invalidation, which is the "
    "defect being fixed. If you want those trades back, raise Max Risk Cap "
    "alongside this; do not lower this to get them.\\n\\nMedian hold also goes "
    "5 -> 8 bars. Rows 1.2 and beyond keep buying premature-stop reduction with "
    "hold time and trade count, and 1.2 is NOT monotone — its stop-out rate is "
    "worse than 0.8 while its trade count is 40% lower. 1.6 is the next setting "
    "worth having if being stopped out matters more to you than frequency.\\n\\n"
    "WHAT WAS TESTED AND REJECTED. The obvious alternative fix is to arm "
    "breakeven earlier — this engine only moves the stop to entry after TP1 "
    "trades, so a trade that runs most of the way to TP1 and reverses is still "
    "a whole loss, and 44% of full stop-outs had already run 0.5R or more in "
    "their favour. Arming on excursion instead was measured:\\n\\n"
    "  build                     TP1    TP2    TP3     BE     SL\\n"
    "  BE after TP1 (current)    55%    17%     8%    47%    43%\\n"
    "  BE at 0.50R excursion     40%    12%     6%    61%    32%\\n"
    "  BE at 0.70R excursion     50%    17%     8%    46%    44%\\n"
    "  BE at 0.85R excursion     52%    21%    10%    37%    51%\\n\\n"
    "It is not a fix. At 0.50R it buys an 11-point drop in stop-outs by "
    "destroying 15 points of TP1 — it scratches the trades that were going to "
    "work. At 0.85R it makes stop-outs WORSE. So no excursion-breakeven option "
    "was added; the stop buffer is where this problem actually lives.\\n\\n"
    "ORIGINAL NOTE — SL is placed at last pivot +/- this ATR buffer. Auto-scales "
    "UP in chop (x1.2) and expansion (x1.3) and never tightens below 1.0x. "
    "Scalp mode clamps the buffer to the Scalp SL Buffer Cap.\\n\\nCounts and "
    "outcome geometry only. No expectancy computed or quoted; the data is "
    "synthetic and no price feed was reachable.")

sub1('''i_slAtr      = input.float(0.5,"SL Buffer Below/Above Pivot (× ATR)",''',
     '''i_slAtr      = input.float(0.8,"SL Buffer Below/Above Pivot (× ATR)",''',
     "sl buffer default")

start = src.index('     tooltip="SL is placed at last pivot ± this ATR buffer.')
end = src.index("\n", start)
src = src[:start] + '     tooltip="%s",' % TIP + src[end:]
print("  ok  sl buffer tooltip")

src = src.replace('indicator("Movement Engine Pro v5.0", shorttitle="ME Pro v5.0"',
                  'indicator("Movement Engine Pro v5.1", shorttitle="ME Pro v5.1"')
src = src.replace('// © ME Institutional — Movement Engine Pro v5.0 (the preset now governs the whole conjunction)',
                  '// © ME Institutional — Movement Engine Pro v5.1 (44% of the stop-outs were the stop, not the market)')
src = src.replace('"ME PRO v5.0"', '"ME PRO v5.1"')

io.open(P, "w", encoding="utf-8").write(src)
print("\nwrote %d bytes" % len(src))
