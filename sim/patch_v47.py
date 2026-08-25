"""ME Pro v4.7 — merged global rows, CRT trigger, Silver Bullet windows."""
import io, sys, shutil

SRC = "/home/user/Claude/MovementEnginePro.v4.6.pine"
P = "/home/user/Claude/MovementEnginePro.v4.7.pine"
shutil.copy(SRC, P)
src = io.open(P, encoding="utf-8").read()


def sub1(old, new, tag):
    global src
    if src.count(old) != 1:
        sys.exit("PATCH %s: expected 1, found %d" % (tag, src.count(old)))
    src = src.replace(old, new)
    print("  ok  %s" % tag)


# ═══ 1. THE DASHBOARD AMBIGUITY ════════════════════════════════════════════
# Columns 1 and 2 are headed BUY and SELL. Any row whose reading is GLOBAL was
# still writing into both of them, so a meter appeared under "SELL" and looked
# like a sell-side reading. Global rows now MERGE across both columns, so the
# layout itself states which is which: split = directional, wide = global.

sub1('''    trendTxt = prismBull ? "▲ BULLISH" : "▼ BEARISH"
    table.cell(dash, 0, 1, "Trend", text_color=dim, text_size=size.tiny, text_halign=text.align_left, bgcolor=color.rgb(12, 12, 18))
    table.cell(dash, 1, 1, trendTxt, text_color=color.white, text_size=size.small, bgcolor=color.new(prismBull ? i_prismUpCol : i_prismDnCol, 25))
    f_cell(2, 1, "age " + str.tostring(prismAge) + " bars", dim)

    rankPct = str.tostring(math.round(nz(prismRank, 0.5) * 100)) + "%"
    table.cell(dash, 0, 2, "Vol Regime", text_color=dim, text_size=size.tiny, text_halign=text.align_left, bgcolor=color.rgb(12, 12, 18))
    f_cell(1, 2, str.upper(prismRegime) + " (" + rankPct + ")", prismRank >= 0.75 ? yel : prismRank <= 0.25 ? dim : wht)
    f_cell(2, 2, f_meter(nz(prismRank, 0.5), 7), prismRank >= 0.75 ? yel : grn)

    table.cell(dash, 0, 3, "Live Multiplier", text_color=dim, text_size=size.tiny, text_halign=text.align_left, bgcolor=color.rgb(12, 12, 18))
    f_cell(1, 3, str.tostring(math.round(prismMult, 2)) + "x ATR", wht)
    f_cell(2, 3, "base " + str.tostring(i_prismBase, "#.0") + " · refr " + str.tostring(i_prismRefr, "#.00"), dim)

    table.cell(dash, 0, 4, "Trail Level", text_color=dim, text_size=size.tiny, text_halign=text.align_left, bgcolor=color.rgb(12, 12, 18))
    f_cell(1, 4, str.tostring(prismLine, format.mintick), prismBull ? grn : red_)
    f_cell(2, 4, prismBull ? "support below" : "resistance above", dim)

    table.cell(dash, 0, 5, "Trail Distance", text_color=dim, text_size=size.tiny, text_halign=text.align_left, bgcolor=color.rgb(12, 12, 18))
    f_cell(1, 5, str.tostring(math.round(prismDist, 2)) + "x ATR", wht)
    f_cell(2, 5, f_meter(math.min(prismDist / 4.0, 1.0), 7), grn)''',
'''    // v4.7: GLOBAL rows are MERGED across the BUY and SELL columns. v4.6 wrote
    // a meter into column 2 on rows that have no side at all, so a volatility
    // bar appeared under the SELL heading and read like a sell-side signal. It
    // was not — it had no side. The layout now answers the question by itself:
    //   SPLIT into two columns  ->  the reading DIFFERS for BUY and SELL
    //   MERGED across the row   ->  ONE reading, applies to both
    // Nothing about the numbers changed; only the cell they live in.
    trendTxt = (prismBull ? "▲ BULLISH" : "▼ BEARISH") + "   ·   age " + str.tostring(prismAge) + " bars"
    table.cell(dash, 0, 1, "Trend", text_color=dim, text_size=size.tiny, text_halign=text.align_left, bgcolor=color.rgb(12, 12, 18))
    table.cell(dash, 1, 1, trendTxt, text_color=color.white, text_size=size.small, bgcolor=color.new(prismBull ? i_prismUpCol : i_prismDnCol, 25))

    rankPct = str.tostring(math.round(nz(prismRank, 0.5) * 100)) + "%"
    table.cell(dash, 0, 2, "Vol Regime", text_color=dim, text_size=size.tiny, text_halign=text.align_left, bgcolor=color.rgb(12, 12, 18))
    f_cell(1, 2, str.upper(prismRegime) + " (" + rankPct + ")   " + f_meter(nz(prismRank, 0.5), 7), prismRank >= 0.75 ? yel : prismRank <= 0.25 ? dim : wht)

    table.cell(dash, 0, 3, "Live Multiplier", text_color=dim, text_size=size.tiny, text_halign=text.align_left, bgcolor=color.rgb(12, 12, 18))
    f_cell(1, 3, str.tostring(math.round(prismMult, 2)) + "x ATR   ·   base " + str.tostring(i_prismBase, "#.0") + " · refr " + str.tostring(i_prismRefr, "#.00"), wht)

    table.cell(dash, 0, 4, "Trail Level", text_color=dim, text_size=size.tiny, text_halign=text.align_left, bgcolor=color.rgb(12, 12, 18))
    f_cell(1, 4, str.tostring(prismLine, format.mintick) + "   ·   " + (prismBull ? "support below" : "resistance above"), prismBull ? grn : red_)

    table.cell(dash, 0, 5, "Trail Distance", text_color=dim, text_size=size.tiny, text_halign=text.align_left, bgcolor=color.rgb(12, 12, 18))
    f_cell(1, 5, str.tostring(math.round(prismDist, 2)) + "x ATR   " + f_meter(math.min(prismDist / 4.0, 1.0), 7), wht)''',
"merge prism rows")

sub1('''    f_cell(1, 15, relVolTxt, relVolCol)
    f_cell(2, 15, relVolTxt, relVolCol)''',
     '''    f_cell(1, 15, relVolTxt, relVolCol)''', "merge rel volume")

sub1('''    f_cell(1, 19, regTxt + " " + str.tostring(math.round(volRegime, 2)) + "×", regCol)
    f_cell(2, 19, regTxt + " " + str.tostring(math.round(volRegime, 2)) + "×", regCol)''',
     '''    f_cell(1, 19, regTxt + " " + str.tostring(math.round(volRegime, 2)) + "× (ATR14/ATR50)", regCol)''',
     "merge atr regime")

sub1('''    f_cell(1, 17, gateTxt, gateCol)
    f_cell(2, 17, nonRevOkBuy ? "BUY ok" : nonRevOkSell ? "SELL ok" : "both blocked", nonRevOkBuy or nonRevOkSell ? grn : yel)''',
     '''    f_cell(1, 17, gateTxt + "   ·   " + (nonRevOkBuy ? "BUY ok" : nonRevOkSell ? "SELL ok" : "both blocked"), gateCol)''',
     "merge gate row")

sub1("""    f_cell(1, 23, trigTxt, trigCol)
    f_cell(2, 23, trigTxt, trigCol)""",
     """    f_cell(1, 23, trigTxt, trigCol)""", "merge triggers")

# header row states the convention
sub1('''    table.cell(dash, 1, 0, "BUY",  text_color=color.new(#00E5FF, 20), bgcolor=color.rgb(15, 15, 20), text_size=size.small)
    table.cell(dash, 2, 0, "SELL", text_color=color.new(#FF3366, 20), bgcolor=color.rgb(15, 15, 20), text_size=size.small)''',
'''    // v4.7: these headings govern SPLIT rows only. A row that spans the full
    // width has no side — it is one global reading.
    table.cell(dash, 1, 0, "BUY",  text_color=color.new(#00E5FF, 20), bgcolor=color.rgb(15, 15, 20), text_size=size.small)
    table.cell(dash, 2, 0, "SELL", text_color=color.new(#FF3366, 20), bgcolor=color.rgb(15, 15, 20), text_size=size.small)''',
"header note")

io.open(P, "w", encoding="utf-8").write(src)
print("\nwrote %d bytes" % len(src))
