"""ME Scalp EA v3.0 — the same deletions v3.0 made to the Pine, made to the EA.

Built by REMOVING from the working v2.5 EA rather than rewriting, so every piece
of hard-won MT5 plumbing survives untouched: the filling-mode probe, lot
normalisation, the spread-as-a-share-of-stop cost guard, and — above all — the
v2.5 server-side take-profit fix and its EnsureProtection() tick guard.
"""
import io, sys, shutil

SRC = "/home/user/Claude/MEScalp_v25.mq5"
P = "/home/user/Claude/MEScalp_v30.mq5"
shutil.copy(SRC, P)
src = io.open(P, encoding="utf-8").read()


def sub1(old, new, tag):
    global src
    if src.count(old) != 1:
        sys.exit("PATCH %s: expected 1, found %d" % (tag, src.count(old)))
    src = src.replace(old, new)
    print("  ok  %s" % tag)


def cut(start, end, tag):
    """Delete everything from `start` through `end`, inclusive."""
    global src
    i = src.find(start)
    j = src.find(end, i)
    if i < 0 or j < 0:
        sys.exit("CUT %s: not found (%d, %d)" % (tag, i, j))
    src = src[:i] + src[j + len(end):]
    print("  ok  cut %s" % tag)


# ── header ────────────────────────────────────────────────────────────────────
sub1("//  v2.5 — THE TAKE-PROFIT WAS NEVER SENT TO THE BROKER.",
"""//  v3.0 — THE SAME ENGINE WITH THE DEAD TWO THIRDS DELETED.
//
//  This is the MT5 port of ME Scalp v3.0. It was built by REMOVING from the
//  v2.5 EA rather than by rewriting, so every piece of MT5 plumbing that took
//  work to get right survives untouched: the filling-mode probe, lot
//  normalisation to the broker's min/max/step, the spread-as-a-share-of-stop
//  cost guard, and above all the v2.5 SERVER-SIDE TAKE-PROFIT fix described
//  further down this header. That fix is the single most important thing in
//  this file and none of it has changed.
//
//  WHAT WAS DELETED, and every deletion was measured on the Pine first:
//
//    THE VWAP BAND, BAND2 AND VALUE-AREA TRIGGERS. Dropping all three is free
//    on both timeframes — 5m TP1 reach goes UP a point, 15m is unchanged:
//
//        5m                            15m
//                       trd/d TP1  SL   trd/d TP1  SL
//        all six         3.05 65% 11%    1.64 61% 23%
//        without them    2.98 66% 11%    1.62 61% 23%
//
//    They were the highest-supply events in the engine and, once v2.5 gated
//    the collapsed-band bug, close to none of the trades. Removing them takes
//    ComputeVwap(), ComputeProfile() and the whole volume profile with them —
//    about 130 lines of per-bar arithmetic gone from OnTick's critical path.
//
//    THE TP1 "SNAP TO STRUCTURE". It NEVER FIRED. TpLevel() pulled TP1 in to
//    VWAP, the band or the POC when one sat nearer than the ATR target AND at
//    least 0.6 units away — a 0.2 ATR window that nothing lands in. Measured
//    on and off, with the band triggers in and out: all four runs returned
//    byte-identical trade counts and outcome mixes. TP1 is now a plain ATR
//    distance like TP2 and TP3.
//
//    THE SCORE'S LOCATION TERM went with the bands, so the quality score is
//    0-4 rather than 0-5. Re-measured after that change: 5m 2.98 -> 2.93
//    trades a day and nothing else moved, 15m identical to two decimals.
//
//    InpSlBuf AND InpStructPad were two inputs doing one job and ADDING — the
//    clearance actually applied was always their sum. They are now one input,
//    InpPad, defaulting to that same 0.45.
//
//    InpMinRisk, InpStructMax and InpAlign are constants now. Alignment is
//    kept ON, not dropped: it is worth about 3 points of TP1 reach for 14% of
//    the trades, which is the first outcome-based evidence it does anything.
//
//  AGAINST v2.3, WHERE THIS LINE OF WORK STARTED:
//
//      5m   4.92 -> 2.93 trd/day, TP1 57% -> 66%, SL 14% -> 11%
//      15m  3.13 -> 1.62 trd/day, TP1 45% -> 61%, SL 26% -> 23%
//
//  Better on every column except supply, which is down 40% and 48%. That is
//  the trade this whole line has been making and it has no free side.
//
//  THOSE NUMBERS COME FROM A SYNTHETIC GENERATOR, not from gold. It can prove
//  a rule dead or free — both are geometry — but it cannot tell you this makes
//  money on XAUUSD at your broker. Run MEScalp.v3.0.strategy.pine in the
//  TradingView Strategy Tester with your real commission and spread for that.
//
//  ─────────────────────────────────────────────────────────────────────────
//  v2.5 — THE TAKE-PROFIT WAS NEVER SENT TO THE BROKER.""",
     "header")

src = src.replace('#property version   "2.50"', '#property version   "3.00"')
src = src.replace("//|                                                  MEScalp_v25.mq5 |",
                  "//|                                                  MEScalp_v30.mq5 |")
src = src.replace("//|                    © ME Institutional — ME Scalp v2.5 for MT5    |",
                  "//|                    © ME Institutional — ME Scalp v3.0 for MT5    |")
src = src.replace('"ME Scalp v2.5  %s %s\\n"', '"ME Scalp v3.0  %s %s\\n"')

io.open(P, "w", encoding="utf-8").write(src)
print("\nstage 1 wrote %d bytes" % len(src))


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 2 — delete the VWAP, the volume profile and the dead TP1 snap
# ══════════════════════════════════════════════════════════════════════════════
src = io.open(P, encoding="utf-8").read()

cut("void ComputeVwap(const MqlRates &r[], int evalShift)",
    "   gProfileOk = true;\n  }\n\n", "ComputeVwap + ComputeProfile")

cut("double TpLevel(bool isBuy, double entry, double unit, double mult, bool snap)",
    "   return(best);\n  }\n\n", "TpLevel")

sub1("""   ComputeVwap(r, s);
   ComputeProfile(r, s);

""", "", "compute calls")

sub1("""double   gPoc = 0.0, gVah = 0.0, gVal = 0.0;
bool     gProfileOk = false;
double   gVwap = 0.0, gU1 = 0.0, gL1 = 0.0, gU2 = 0.0, gL2 = 0.0;
double   gEr = 0.0;""",
     "double   gEr = 0.0;", "vwap/profile globals")

# ── inputs ────────────────────────────────────────────────────────────────────
sub1("""input bool            InpUseBand     = true;           // VWAP band rejection
input bool            InpUseValue    = true;           // Value-area rejection
input double          InpBandMinW    = 0.30;           // Band must be this wide to count (xATR) - 0 = old behaviour""",
"""// v3.0: the VWAP band, band2 and value-area triggers are GONE. Dropping all
// three measured free on both timeframes — see the header. Their inputs, the
// band-width gate and the whole volume profile went with them.""",
     "trigger inputs")

sub1('input bool            InpAlign       = true;           // Only trade WITH the leg in progress\n', "",
     "align input")

sub1("""input double          InpStructPad   = 0.25;           // Structure pad beyond invalidation (xATR) - ADDS TO InpSlBuf
input double          InpStructMax   = 4.00;           // Reject setup if structural risk exceeds (xATR)
input double          InpMinRisk     = 0.40;           // Min risk (xATR)
input double          InpSlBuf       = 0.20;           // SL buffer past invalidation (xATR) - ADDS TO InpStructPad; total shown on panel""",
"""// v3.0: InpSlBuf and InpStructPad were two inputs doing one job and ADDING, so
// the clearance actually applied was always their sum. One input now, at that
// same 0.45. InpMinRisk and InpStructMax became the constants below.
input double          InpPad         = 0.45;           // Stop clearance beyond invalidation (xATR)""",
     "pad inputs")

sub1("""int      hAtr           = INVALID_HANDLE;""",
"""// v3.0 constants. These were inputs nobody should have to reason about, and no
// measurement ever argued for moving them.
#define ME_MIN_RISK  0.40      // stop floor in ATR, so a stop cannot be absurd
#define ME_MAX_RISK  4.00      // decline a setup whose structural stop is wider

int      hAtr           = INVALID_HANDLE;""",
     "constants")

io.open(P, "w", encoding="utf-8").write(src)
print("\nstage 2 wrote %d bytes" % len(src))


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 3 — EvaluateBar: three triggers, a four-term score, one pad
# ══════════════════════════════════════════════════════════════════════════════
src = io.open(P, encoding="utf-8").read()

sub1("""   // v2.5 THE BAND MUST HAVE WIDTH. The deviation is accumulated from the
   // session anchor, so on the first bars after it the deviation comes from ONE
   // SAMPLE and the bands collapse onto VWAP: gU1 == gL1 == gVwap. The test
   // below is then true of any bar that closes above its own low, and the
   // engine was reading arithmetic as a rejection. Measured over 360 simulated
   // days, that family was a third of all 15m trades and reached TP1 25% of the
   // time against 66% for FVG.
   bool bandOk = ((gU1 - gL1) >= atr * InpBandMinW);
   bool bandBull  = InpUseBand && bandOk && r[s].low  <= gL1 && r[s].close > gL1 && cp >= 0.55;
   bool bandBear  = InpUseBand && bandOk && r[s].high >= gU1 && r[s].close < gU1 && cp <= 0.45;
   bool band2Bull = InpUseBand && bandOk && r[s].low  <= gL2 && r[s].close > gL2 && cp >= 0.55;
   bool band2Bear = InpUseBand && bandOk && r[s].high >= gU2 && r[s].close < gU2 && cp <= 0.45;

   bool valBull = InpUseValue && gProfileOk && r[s].low  <= gVal && r[s].close > gVal && cp >= 0.55;
   bool valBear = InpUseValue && gProfileOk && r[s].high >= gVah && r[s].close < gVah && cp <= 0.45;

   int nBull = (mssBull?1:0)+(fvgBull?1:0)+(swBull?1:0)+(bandBull?1:0)+(band2Bull?1:0)+(valBull?1:0);
   int nBear = (mssBear?1:0)+(fvgBear?1:0)+(swBear?1:0)+(bandBear?1:0)+(band2Bear?1:0)+(valBear?1:0);
   if(nBull == 0 && nBear == 0) { gLastBlock = "no trigger"; return; }

   // Priority order decides the INVALIDATION the stop is built from, so it is
   // not cosmetic — it is kept identical to the indicator's.
   string bullName = mssBull?"MSS":fvgBull?"FVG":swBull?"SWEEP":bandBull?"BAND":band2Bull?"BAND2":"VALUE";
   string bearName = mssBear?"MSS":fvgBear?"FVG":swBear?"SWEEP":bandBear?"BAND":band2Bear?"BAND2":"VALUE";
   double bullInval = mssBull ? (hasPL ? lastPL : r[s].low)  : fvgBull ? fvgBInv : r[s].low;
   double bearInval = mssBear ? (hasPH ? lastPH : r[s].high) : fvgBear ? fvgSInv : r[s].high;

   // ---------------- quality score, 0-5 ----------------
   // Location scores only for a trigger that is not itself a band rejection —
   // a band trigger sits at a band by construction and counting it is billing
   // one fact twice. Keyed to the SELECTED trigger, as in v2.0.
   int sLocB = (bullName == "BAND2") ? 1 : (bullName == "BAND") ? 0 : (r[s].close <= gL1 * 1.002 ? 1 : 0);
   int sLocS = (bearName == "BAND2") ? 1 : (bearName == "BAND") ? 0 : (r[s].close >= gU1 * 0.998 ? 1 : 0);
   int scoreBull = (relV >= 1.15?1:0) + (body >= atr*0.45?1:0) + (cp >= 0.65?1:0) + (nBull >= 2?1:0) + sLocB;
   int scoreBear = (relV >= 1.15?1:0) + (body >= atr*0.45?1:0) + (cp <= 0.35?1:0) + (nBear >= 2?1:0) + sLocS;""",
"""   int nBull = (mssBull?1:0)+(fvgBull?1:0)+(swBull?1:0);
   int nBear = (mssBear?1:0)+(fvgBear?1:0)+(swBear?1:0);
   if(nBull == 0 && nBear == 0) { gLastBlock = "no trigger"; return; }

   // Priority order decides the INVALIDATION the stop is built from, so it is
   // not cosmetic — it is kept identical to the indicator's.
   string bullName = mssBull?"MSS":fvgBull?"FVG":"SWEEP";
   string bearName = mssBear?"MSS":fvgBear?"FVG":"SWEEP";
   double bullInval = mssBull ? (hasPL ? lastPL : r[s].low)  : fvgBull ? fvgBInv : r[s].low;
   double bearInval = mssBear ? (hasPH ? lastPH : r[s].high) : fvgBear ? fvgSInv : r[s].high;

   // ---------------- quality score, 0-4 ----------------
   // v3.0: this was 0-5. The fifth term scored LOCATION at a VWAP band, and it
   // went with the bands. Re-measured after removing it: 5m 2.98 -> 2.93 trades
   // a day and nothing else moved; 15m identical to two decimals.
   int scoreBull = (relV >= 1.15?1:0) + (body >= atr*0.45?1:0) + (cp >= 0.65?1:0) + (nBull >= 2?1:0);
   int scoreBear = (relV >= 1.15?1:0) + (body >= atr*0.45?1:0) + (cp <= 0.35?1:0) + (nBear >= 2?1:0);""",
     "triggers and score")

sub1("""   double pad = atr * InpStructPad;
   double padBull = pad + ((bullName == "MSS") ? atr * InpBreakPad : 0.0);
   double padBear = pad + ((bearName == "MSS") ? atr * InpBreakPad : 0.0);
   double slBull = MathMin(bullInval, r[s].close - atr * InpMinRisk) - atr * InpSlBuf - padBull;
   double slBear = MathMax(bearInval, r[s].close + atr * InpMinRisk) + atr * InpSlBuf + padBear;
   double riskBull = r[s].close - slBull;
   double riskBear = slBear - r[s].close;

   bool riskOkBull = (riskBull >= atr * InpMinRisk * 0.5) && (riskBull <= atr * InpStructMax);
   bool riskOkBear = (riskBear >= atr * InpMinRisk * 0.5) && (riskBear <= atr * InpStructMax);

   bool regimeBuy  = gInTrend && (!InpAlign ||  gLegUp);
   bool regimeSell = gInTrend && (!InpAlign || !gLegUp);""",
"""   double padBull = atr * (InpPad + ((bullName == "MSS") ? InpBreakPad : 0.0));
   double padBear = atr * (InpPad + ((bearName == "MSS") ? InpBreakPad : 0.0));
   double slBull = MathMin(bullInval, r[s].close - atr * ME_MIN_RISK) - padBull;
   double slBear = MathMax(bearInval, r[s].close + atr * ME_MIN_RISK) + padBear;
   double riskBull = r[s].close - slBull;
   double riskBear = slBear - r[s].close;

   bool riskOkBull = (riskBull >= atr * ME_MIN_RISK * 0.5) && (riskBull <= atr * ME_MAX_RISK);
   bool riskOkBear = (riskBear >= atr * ME_MIN_RISK * 0.5) && (riskBear <= atr * ME_MAX_RISK);

   // v3.0: alignment is always on. It was an input defaulting to true, and it
   // is worth about 3 points of TP1 reach for 14% of the trades — the first
   // outcome-based evidence it does anything, so it stops being optional.
   bool regimeBuy  = gInTrend &&  gLegUp;
   bool regimeSell = gInTrend && !gLegUp;""",
     "stop and regime")

sub1("""   double t1 = TpLevel(isBuy, entry, atr, InpTp1Atr, true);""",
"""   // v3.0: a plain ATR distance. Through v2.5 this ran TpLevel(..., snap=true),
   // which pulled TP1 in to VWAP, the band or the POC when one sat nearer than
   // the ATR target AND at least 0.6 units away. That is a 0.2 ATR window and
   // nothing lands in it — measured on and off, the outcome mixes came back
   // byte-identical. It was dead code.
   double t1 = isBuy ? entry + atr*InpTp1Atr : entry - atr*InpTp1Atr;""",
     "tp1 snap")

sub1("""// TP1 is pulled IN to the nearer of the VWAP band, the VWAP itself and the POC
// when one of them sits closer than the ATR distance and is still at least
// 0.6 units away — the same rule the indicator uses.
""", "", "tplevel comment")

sub1('''      "VWAP     %.*f   band +-1s %.*f / %.*f\\n"
      "profile  %s\\n"
''', "", "panel vwap lines")

sub1('''      _Digits, gVwap, _Digits, gU1, _Digits, gL1,
      gProfileOk ? StringFormat("POC %.*f  VAH %.*f  VAL %.*f",
                                _Digits, gPoc, _Digits, gVah, _Digits, gVal)
                 : "building",
''', "", "panel vwap args")

sub1("""      InpBrokerTp == 2 ? "(server TP OFF)"
                       : StringFormat("pad %.2f/%.2f ATR", InpSlBuf + InpStructPad,
                                      InpSlBuf + InpStructPad + InpBreakPad),""",
"""      InpBrokerTp == 2 ? "(server TP OFF)"
                       : StringFormat("pad %.2f/%.2f ATR", InpPad, InpPad + InpBreakPad),""",
     "panel pad")

io.open(P, "w", encoding="utf-8").write(src)
print("\\nstage 3 wrote %d bytes" % len(src))


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 4 — the score threshold was hardcoded here while the Pine exposes it,
# and a bridging note so the inherited v2.5 changelog does not send a reader
# hunting for inputs this build no longer has.
# ══════════════════════════════════════════════════════════════════════════════
src = io.open(P, encoding="utf-8").read()

sub1("""input int             InpErLen       = 30;             // Regime lookback (bars) - was 20; 30 measured better, 40 gives it back""",
"""input int             InpErLen       = 30;             // Regime lookback (bars) - was 20; 30 measured better, 40 gives it back
// v3.0: the indicator exposes this and the EA hardcoded it at 1. Raising it
// does NOT reduce losses -- it raises them on both timeframes while collapsing
// the share of trades that resolve nothing, converting unresolved trades into
// resolved ones in BOTH directions:
//   need   5m trd/d TP1  SL TIME     15m trd/d TP1  SL TIME
//   0/4        3.23 64% 11%  25%          1.71 59% 22%  18%
//   1/4        2.93 66% 11%  22%          1.62 61% 23%  16%
//   2/4        2.03 72% 13%  15%          1.36 66% 26%   8%
input int             InpScore       = 1;              // Quality score required (of 4)""",
     "score input")

sub1("""   bool buySig  = (nBull>0) && allowLong  && barBull && riskOkBull && costOkBull && scoreBull >= 1 && regimeBuy;
   bool sellSig = (nBear>0) && allowShort && barBear && riskOkBear && costOkBear && scoreBear >= 1 && regimeSell;""",
"""   bool buySig  = (nBull>0) && allowLong  && barBull && riskOkBull && costOkBull && scoreBull >= InpScore && regimeBuy;
   bool sellSig = (nBear>0) && allowShort && barBear && riskOkBear && costOkBear && scoreBear >= InpScore && regimeSell;""",
     "score wiring")

sub1("""      gLastBlock = BlockReason(nBull>0, barBull, riskOkBull, scoreBull>=1, regimeBuy,""",
"""      gLastBlock = BlockReason(nBull>0, barBull, riskOkBull, scoreBull>=InpScore, regimeBuy,""",
     "block reason bull")

sub1("""                               nBear>0, barBear, riskOkBear, scoreBear>=1, regimeSell);""",
"""                               nBear>0, barBear, riskOkBear, scoreBear>=InpScore, regimeSell);""",
     "block reason bear")

sub1("""//  ─────────────────────────────────────────────────────────────────────────
//  v2.5 — THE TAKE-PROFIT WAS NEVER SENT TO THE BROKER.""",
"""//  ─────────────────────────────────────────────────────────────────────────
//  EVERYTHING BELOW THIS LINE IS THE CHANGELOG OF EARLIER BUILDS, kept because
//  it is the record of why the code looks the way it does. It names inputs
//  this version no longer has — InpSlBuf, InpStructPad, InpMinRisk,
//  InpStructMax, InpAlign, InpUseBand, InpUseValue, InpBandMinW — and
//  functions it no longer has: ComputeVwap, ComputeProfile, TpLevel. Do not go
//  looking for them; see the v3.0 block above for what replaced each one.
//
//  v2.5 — THE TAKE-PROFIT WAS NEVER SENT TO THE BROKER.""",
     "changelog bridge")

io.open(P, "w", encoding="utf-8").write(src)
print("\nstage 4 wrote %d bytes" % len(src))
