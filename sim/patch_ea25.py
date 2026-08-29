"""ME Scalp EA v2.5 — the take-profit was never sent to the broker.

The bug the user reported, and it is real: OpenTrade calls

    trade.Buy(lots, _Symbol, 0.0, sl, 0.0, ...)
                                    ^^^ tp

CTrade::Buy takes (volume, symbol, price, sl, tp, comment). The fifth argument
is the take-profit and it is passed 0.0, so every position this EA has ever
opened carried a server-side STOP and NO server-side TARGET.
"""
import io, sys, shutil

SRC = "/home/user/Claude/MEScalp_v23.mq5"
P = "/home/user/Claude/MEScalp_v25.mq5"
shutil.copy(SRC, P)
src = io.open(P, encoding="utf-8").read()


def sub1(old, new, tag):
    global src
    if src.count(old) != 1:
        sys.exit("PATCH %s: expected 1, found %d" % (tag, src.count(old)))
    src = src.replace(old, new)
    print("  ok  %s" % tag)


# ── header ────────────────────────────────────────────────────────────────────
sub1("""//  v2.3 — TP1 IS NOW COUNTED, AND THE TWO STOP PADS ARE DECLARED.""",
"""//  v2.5 — THE TAKE-PROFIT WAS NEVER SENT TO THE BROKER.
//
//  REPORTED: "the bot does not have tp on mt5 only sl which lead to more
//  loses". That is exactly right, and the consequence is worse than a missing
//  column in the terminal.
//
//  THE BUG, one argument wide:
//
//      trade.Buy(lots, _Symbol, 0.0, sl, 0.0, "MESC " + tag);
//                                        ^^^ this is the TAKE-PROFIT
//
//  CTrade::Buy is (volume, symbol, price, sl, tp, comment). The fifth argument
//  was 0.0 on every order this EA has ever sent, so every position opened with
//  a server-side stop and no server-side target. The same 0.0 was written again
//  by the breakeven move:
//
//      trade.PositionModify(pos.Ticket(), be, 0.0);
//
//  and AdoptExistingPosition compounded it, setting planTp1Done = planTp2Done =
//  true on any position it picked up after a restart — so an adopted trade had
//  no targets at the broker AND none in the EA's memory. It could only ever end
//  at its stop or the time stop.
//
//  WHY THIS COSTS MONEY, and it is not subtle. The targets lived only inside
//  OnTick. The stop lived at the broker. So:
//
//      the LOSING side was guaranteed by the server
//      the WINNING side required my code to be running
//
//  Terminal closed, AutoTrading off, chart removed, VPS rebooted, connection
//  dropped, EA recompiled — the stop still works and the targets do not. Every
//  one of those events converts an open trade into a stop-or-nothing bet. That
//  asymmetry is a straight bias toward losses and it is the defect, not the
//  signal logic.
//
//  THE FIX. Every position now carries a real server-side take-profit.
//
//    - InpBrokerTp chooses which level goes to the server. Default TP3, so the
//      EA keeps scaling out at TP1 and TP2 while it is alive and the position
//      still has a target if it is not.
//    - The breakeven modify writes SL *and* TP. It never sends 0 again.
//    - SL and TP are re-asserted on the remainder after each partial close,
//      because some brokers drop the levels on a partial.
//    - EnsureProtection() runs every tick: if a position of ours is missing its
//      stop or its target, it is repaired on the spot. This also rescues
//      positions opened by an older build.
//    - AdoptExistingPosition now READS pos.TakeProfit() and rebuilds the plan
//      from it instead of assuming every leg was already taken.
//
//  SafeTarget() mirrors SafeStop(): a broker refuses a target inside
//  SYMBOL_TRADE_STOPS_LEVEL just as it refuses a stop, and an unchecked TP is a
//  rejected order rather than a missing one.
//
//  ─────────────────────────────────────────────────────────────────────────
//  ALSO IN THIS BUILD, carried over from the indicator, and both are BUGS
//  rather than tuning:
//
//  THE VWAP BAND TRIGGER FIRED ON ARITHMETIC. The deviation is accumulated
//  from the session anchor, so on the first bars after it the deviation comes
//  from ONE SAMPLE and the bands collapse: gU1 == gL1 == gVwap. The test
//  "low <= gL1 && close > gL1" is then true of any bar that closes above its
//  own low. Measured over 360 simulated days that family was a third of all
//  15m trades, reached TP1 25% of the time against 66% for FVG, and its median
//  hold sat exactly on the 12-bar time stop. InpBandMinW (0.30 ATR) requires a
//  band to have width before it counts as a level.
//
//  MSS GETS ITS OWN STOP PAD. It is the only family stopping beyond a PIVOT
//  rather than a bar extreme, and on 15m that pivot is often a few ticks from
//  the entry: 36% stop-outs against 9% for FVG. InpBreakPad (0.20 ATR) is
//  added to the shared pad for MSS only.
//
//  Regime lookback default 20 -> 30, on a user report that measured out.
//
//  NOT PORTED FROM THE INDICATOR: the v2.4 confirmation bar. It needs the
//  trigger state of the previous bar carried forward, which is a real refactor
//  of EvaluateBar, and I am not shipping an untested refactor in the same
//  build as a safety fix. It stays in the Pine until the strategy tester says
//  the engine is worth porting further.
//
//  ─────────────────────────────────────────────────────────────────────────
//  v2.3 — TP1 IS NOW COUNTED, AND THE TWO STOP PADS ARE DECLARED.""",
     "header")

src = src.replace('#property version   "2.30"', '#property version   "2.50"')
src = src.replace("//|                                                  MEScalp_v23.mq5 |",
                  "//|                                                  MEScalp_v25.mq5 |")
src = src.replace("//|                    © ME Institutional — ME Scalp v2.3 for MT5    |",
                  "//|                    © ME Institutional — ME Scalp v2.5 for MT5    |")
src = src.replace('"ME Scalp v2.3  %s %s\\n"', '"ME Scalp v2.5  %s %s\\n"')

# ── inputs ────────────────────────────────────────────────────────────────────
sub1('input int             InpErLen       = 20;             // Regime lookback (bars)',
     'input int             InpErLen       = 30;             // Regime lookback (bars) - was 20; 30 measured better, 40 gives it back',
     "lookback default")

sub1('input bool            InpUseValue    = true;           // Value-area rejection',
'''input bool            InpUseValue    = true;           // Value-area rejection
input double          InpBandMinW    = 0.30;           // Band must be this wide to count (xATR) - 0 = old behaviour''',
     "band width input")

sub1('input bool            InpBeAfterTp1  = true;           // Move stop to breakeven after TP1',
'''input double          InpBreakPad    = 0.20;           // Extra stop pad for MSS breaks (xATR)
input bool            InpBeAfterTp1  = true;           // Move stop to breakeven after TP1
// v2.5 SERVER-SIDE TAKE-PROFIT. Through v2.3 this did not exist and every
// position was opened with a stop and no target.
//   0 = TP3   the full target goes to the server. The EA still scales out at
//             TP1 and TP2 while it is running; if it stops running the trade
//             still has somewhere to go. This is the default.
//   1 = TP1   the first target goes to the server, which GUARANTEES the exit
//             but lets the broker close the WHOLE position there, so the
//             scale-out never happens. Choose it if you would rather bank the
//             high-probability target than run the position.
//   2 = off   v2.3 behaviour. Do not use it; it is here so the old build can
//             be reproduced.
input int             InpBrokerTp    = 0;              // Server-side TP: 0 TP3, 1 TP1, 2 off''',
     "broker tp input")

io.open(P, "w", encoding="utf-8").write(src)
print("\nstage 1 wrote %d bytes" % len(src))


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 2 — the fix itself
# ══════════════════════════════════════════════════════════════════════════════
src = io.open(P, encoding="utf-8").read()

sub1('''double SafeStop(bool isBuy, double price, double stop)
  {
   long stopsPt = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double minDist = stopsPt * _Point;
   if(minDist <= 0.0) minDist = 2 * _Point;
   if(isBuy)  { if(price - stop < minDist) stop = price - minDist; }
   else       { if(stop - price < minDist) stop = price + minDist; }
   return(NormalizeDouble(stop, _Digits));
  }''',
'''double SafeStop(bool isBuy, double price, double stop)
  {
   long stopsPt = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double minDist = stopsPt * _Point;
   if(minDist <= 0.0) minDist = 2 * _Point;
   if(isBuy)  { if(price - stop < minDist) stop = price - minDist; }
   else       { if(stop - price < minDist) stop = price + minDist; }
   return(NormalizeDouble(stop, _Digits));
  }

// v2.5 The mirror of SafeStop for the TARGET side. A broker refuses a take
// profit inside SYMBOL_TRADE_STOPS_LEVEL exactly as it refuses a stop, and an
// unchecked TP produces a REJECTED ORDER rather than a missing one — which is
// a worse failure than the bug this release fixes.
double SafeTarget(bool isBuy, double price, double tp)
  {
   if(tp <= 0.0) return(0.0);
   long stopsPt = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double minDist = stopsPt * _Point;
   if(minDist <= 0.0) minDist = 2 * _Point;
   if(isBuy)  { if(tp - price < minDist) tp = price + minDist; }
   else       { if(price - tp < minDist) tp = price - minDist; }
   return(NormalizeDouble(tp, _Digits));
  }

// Which level goes to the server. See the InpBrokerTp comment in the inputs.
double BrokerTp(bool isBuy, double price, double t1, double t3)
  {
   if(InpBrokerTp == 2) return(0.0);                 // v2.3 behaviour, on request
   return(SafeTarget(isBuy, price, InpBrokerTp == 1 ? t1 : t3));
  }''',
     "SafeTarget")

sub1('''   bool ok = isBuy ? trade.Buy(lots, _Symbol, 0.0, sl, 0.0, "MESC " + tag)
                   : trade.Sell(lots, _Symbol, 0.0, sl, 0.0, "MESC " + tag);''',
'''   // v2.5 THE FIX. The fifth argument is the take-profit and it was 0.0 in
   // every build up to v2.3, so the stop was guaranteed by the server and the
   // target was not. A position is now opened with BOTH.
   double refPx = isBuy ? sym.Ask() : sym.Bid();
   double tpSrv = BrokerTp(isBuy, refPx, t1, t3);
   bool ok = isBuy ? trade.Buy(lots, _Symbol, 0.0, sl, tpSrv, "MESC " + tag)
                   : trade.Sell(lots, _Symbol, 0.0, sl, tpSrv, "MESC " + tag);''',
     "order tp")

sub1('''   planTag     = tag;
   lastSignalBar  = planOpenBar;''',
'''   planTag     = tag;
   planTpSrv   = tpSrv;
   lastSignalBar  = planOpenBar;''',
     "store tpSrv")

sub1('''   PrintFormat("ME Scalp %s %s %.2f lots @ %.*f | SL %.*f | TP %.*f / %.*f / %.*f | %d legs",
               isBuy ? "BUY" : "SELL", tag, lots, _Digits, planEntry,
               _Digits, planSl, _Digits, planTp1, _Digits, planTp2, _Digits, planTp3, legs);''',
'''   PrintFormat("ME Scalp %s %s %.2f lots @ %.*f | SL %.*f | TP %.*f / %.*f / %.*f | server TP %.*f | %d legs",
               isBuy ? "BUY" : "SELL", tag, lots, _Digits, planEntry,
               _Digits, planSl, _Digits, planTp1, _Digits, planTp2, _Digits, planTp3,
               _Digits, planTpSrv, legs);''',
     "open log")

sub1('''int      gTaken   = 0;
int      gTp1Hit  = 0;''',
'''int      gTaken   = 0;
int      gTp1Hit  = 0;
int      gTp2Hit  = 0;
// v2.5 the level actually sitting at the broker, kept so the breakeven modify
// and every re-assert can write it back instead of overwriting it with 0.
double   planTpSrv = 0.0;''',
     "state")

sub1('''         double be = SafeStop(planIsBuy, px, planEntry);
         if(trade.PositionModify(pos.Ticket(), be, 0.0)) { planSl = be; planAtBe = true; }''',
'''         // v2.5: this used to pass 0.0 as the take-profit, so the breakeven
         // move DELETED the target as well as tightening the stop.
         double be = SafeStop(planIsBuy, px, planEntry);
         if(trade.PositionModify(pos.Ticket(), be, planTpSrv)) { planSl = be; planAtBe = true; }''',
     "be modify")

sub1('''      if(vol - minL >= minL) trade.PositionClosePartial(pos.Ticket(), NormaliseLots(vol / 3.0));
      if(InpBeAfterTp1 && !planAtBe)''',
'''      if(vol - minL >= minL)
        {
         trade.PositionClosePartial(pos.Ticket(), NormaliseLots(vol / 3.0));
         ReassertLevels();      // some brokers drop SL/TP on a partial close
        }
      if(InpBeAfterTp1 && !planAtBe)''',
     "tp1 partial reassert")

sub1('''      planTp2Done = true;
      if(vol - minL >= minL) trade.PositionClosePartial(pos.Ticket(), NormaliseLots(vol / 2.0));
      return;''',
'''      planTp2Done = true;
      gTp2Hit++;
      PrintFormat("ME Scalp TP2 hit @ %.*f | %s %s | TP2 reach %d/%d = %.0f%%",
                  _Digits, px, planIsBuy ? "LONG" : "SHORT", planTag,
                  gTp2Hit, gTaken, gTaken > 0 ? 100.0 * gTp2Hit / gTaken : 0.0);
      if(vol - minL >= minL)
        {
         trade.PositionClosePartial(pos.Ticket(), NormaliseLots(vol / 2.0));
         ReassertLevels();
        }
      return;''',
     "tp2 partial reassert")

sub1('''void ManageOpenTrade()
  {
   if(!SelectOwnPosition()) { ClearPlan(); return; }''',
'''// v2.5 Re-send the levels the plan says should be on the position. Called after
// every partial close, because a partial is a separate deal and some brokers
// return the remainder without its stop or its target.
void ReassertLevels()
  {
   if(!SelectOwnPosition()) return;
   double haveSl = pos.StopLoss();
   double haveTp = pos.TakeProfit();
   bool needSl = (planSl > 0.0) && (MathAbs(haveSl - planSl) > _Point / 2.0);
   bool needTp = (planTpSrv > 0.0) && (MathAbs(haveTp - planTpSrv) > _Point / 2.0);
   if(needSl || needTp)
      trade.PositionModify(pos.Ticket(),
                           planSl    > 0.0 ? planSl    : haveSl,
                           planTpSrv > 0.0 ? planTpSrv : haveTp);
  }

// v2.5 THE GUARD. Runs on every tick. A position of ours must never sit at the
// broker without both a stop and a target — that asymmetry is the whole reason
// this release exists. This also repairs positions opened by an older build,
// which have no server-side TP at all.
void EnsureProtection()
  {
   if(!SelectOwnPosition()) return;
   bool isBuy   = (pos.PositionType() == POSITION_TYPE_BUY);
   double entry = pos.PriceOpen();
   double haveSl = pos.StopLoss();
   double haveTp = pos.TakeProfit();
   double wantSl = haveSl;
   double wantTp = haveTp;

   if(haveSl <= 0.0)
     {
      // No stop at all. Rebuild one from the plan if we have it, otherwise from
      // ATR, and say so in the log — a naked position is not a normal state.
      double a = (gAtr > 0.0) ? gAtr : (sym.Ask() - sym.Bid()) * 20.0;
      double fallback = isBuy ? entry - a * 1.5 : entry + a * 1.5;
      wantSl = SafeStop(isBuy, isBuy ? sym.Bid() : sym.Ask(),
                        (planActive && planSl > 0.0) ? planSl : fallback);
      PrintFormat("ME Scalp: position had NO STOP - setting %.*f", _Digits, wantSl);
     }
   if(haveTp <= 0.0 && InpBrokerTp != 2)
     {
      double a = (gAtr > 0.0) ? gAtr : (sym.Ask() - sym.Bid()) * 20.0;
      double fallback = isBuy ? entry + a * InpTp3Atr : entry - a * InpTp3Atr;
      wantTp = SafeTarget(isBuy, isBuy ? sym.Bid() : sym.Ask(),
                          (planActive && planTpSrv > 0.0) ? planTpSrv : fallback);
      PrintFormat("ME Scalp: position had NO TAKE-PROFIT - setting %.*f", _Digits, wantTp);
     }
   if(wantSl != haveSl || wantTp != haveTp)
      if(trade.PositionModify(pos.Ticket(), wantSl, wantTp))
        {
         planSl    = wantSl;
         planTpSrv = wantTp;
        }
  }

void ManageOpenTrade()
  {
   if(!SelectOwnPosition()) { ClearPlan(); return; }
   EnsureProtection();''',
     "guards")

sub1('''   planSl      = pos.StopLoss();
   planTp1Done = true;                     // unknown, so assume de-risked
   planTp2Done = true;
   planAtBe    = (MathAbs(planSl - planEntry) < 2 * _Point);
   barsSinceEntry = 0;
   Print("ME Scalp: adopted an existing position; TP legs assumed already taken");''',
'''   planSl      = pos.StopLoss();
   planTpSrv   = pos.TakeProfit();
   // v2.5: v2.3 assumed both TP legs were already taken, which left an adopted
   // position with no targets in the EA's memory AND none at the broker - it
   // could only ever end at its stop. The server-side TP is the record of what
   // the plan was, so rebuild from it rather than guessing.
   planAtBe    = (MathAbs(planSl - planEntry) < 2 * _Point);
   if(planTpSrv > 0.0 && InpBrokerTp == 0)
     {
      // The server carries TP3, so the ATR ratios recover the other two.
      double span = MathAbs(planTpSrv - planEntry);
      double unit = (InpTp3Atr > 0.0) ? span / InpTp3Atr : 0.0;
      int    dir  = planIsBuy ? 1 : -1;
      planTp3 = planTpSrv;
      planTp2 = planEntry + dir * unit * InpTp2Atr;
      planTp1 = planEntry + dir * unit * InpTp1Atr;
      // Breakeven already armed means TP1 must have filled at some point.
      planTp1Done = planAtBe;
      planTp2Done = false;
      PrintFormat("ME Scalp: adopted a position; rebuilt TP %.*f / %.*f / %.*f from the server TP",
                  _Digits, planTp1, _Digits, planTp2, _Digits, planTp3);
     }
   else
     {
      planTp1Done = true;                  // genuinely unknown, so stand aside
      planTp2Done = true;
      Print("ME Scalp: adopted a position with no server TP; leaving its legs alone");
     }
   barsSinceEntry = 0;''',
     "adoption")

sub1("   planActive = false; planTp1Done = false; planTp2Done = false; planAtBe = false;",
     "   planActive = false; planTp1Done = false; planTp2Done = false; planAtBe = false;\n   planTpSrv  = 0.0;",
     "clear plan")

io.open(P, "w", encoding="utf-8").write(src)
print("\nstage 2 wrote %d bytes" % len(src))


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 3 — gAtr (the guard needs it), the band width gate, the MSS pad, panel
# ══════════════════════════════════════════════════════════════════════════════
src = io.open(P, encoding="utf-8").read()

sub1("double   gEr = 0.0;",
'''double   gEr = 0.0;
// v2.5 the last ATR EvaluateBar computed, published so EnsureProtection can
// rebuild a level for a position whose plan the EA no longer holds.
double   gAtr = 0.0;''',
     "gAtr global")

sub1("   double atr = AtrAt(s);",
     "   double atr = AtrAt(s);\n   gAtr = atr;",
     "gAtr publish")

# ── the band width gate ───────────────────────────────────────────────────────
sub1('''   bool bandBull  = InpUseBand && r[s].low  <= gL1 && r[s].close > gL1 && cp >= 0.55;
   bool bandBear  = InpUseBand && r[s].high >= gU1 && r[s].close < gU1 && cp <= 0.45;
   bool band2Bull = InpUseBand && r[s].low  <= gL2 && r[s].close > gL2 && cp >= 0.55;
   bool band2Bear = InpUseBand && r[s].high >= gU2 && r[s].close < gU2 && cp <= 0.45;''',
'''   // v2.5 THE BAND MUST HAVE WIDTH. The deviation is accumulated from the
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
   bool band2Bear = InpUseBand && bandOk && r[s].high >= gU2 && r[s].close < gU2 && cp <= 0.45;''',
     "band width gate")

# ── per-family stop pad ───────────────────────────────────────────────────────
sub1('''   double pad = atr * InpStructPad;
   double slBull = MathMin(bullInval, r[s].close - atr * InpMinRisk) - atr * InpSlBuf - pad;
   double slBear = MathMax(bearInval, r[s].close + atr * InpMinRisk) + atr * InpSlBuf + pad;''',
'''   // v2.5 MSS takes its own extra clearance. It is the only family stopping
   // beyond a PIVOT rather than a bar extreme, and on 15m that pivot is often a
   // few ticks from the entry: 36% stop-outs against 9% for FVG.
   double pad = atr * InpStructPad;
   double padBull = pad + ((bullName == "MSS") ? atr * InpBreakPad : 0.0);
   double padBear = pad + ((bearName == "MSS") ? atr * InpBreakPad : 0.0);
   double slBull = MathMin(bullInval, r[s].close - atr * InpMinRisk) - atr * InpSlBuf - padBull;
   double slBear = MathMax(bearInval, r[s].close + atr * InpMinRisk) + atr * InpSlBuf + padBear;''',
     "mss pad")

# ── panel ─────────────────────────────────────────────────────────────────────
sub1('''      "TP1      reach %s   |  stop pad %.2f ATR\\n"
      "trade    %s\\n"''',
'''      "TP1/TP2  %s\\n"
      "server   SL %.*f   TP %.*f   %s\\n"
      "trade    %s\\n"''',
     "panel format")

sub1('''      gTaken > 0 ? StringFormat("%.0f%%  (%d/%d)", 100.0 * gTp1Hit / gTaken, gTp1Hit, gTaken)
                 : "no trades yet",
      InpSlBuf + InpStructPad,
      st, gLastBlock));''',
'''      gTaken > 0 ? StringFormat("reach %.0f%% / %.0f%%   (%d, %d of %d)",
                                100.0 * gTp1Hit / gTaken, 100.0 * gTp2Hit / gTaken,
                                gTp1Hit, gTp2Hit, gTaken)
                 : "no trades yet",
      // v2.5 THE LINE THIS RELEASE EXISTS FOR. If the TP column reads 0.00
      // while a trade is open, the position is sitting at the broker with a
      // guaranteed loss and no guaranteed win, which is the v2.3 bug.
      _Digits, planActive ? planSl : 0.0,
      _Digits, planActive ? planTpSrv : 0.0,
      InpBrokerTp == 2 ? "(server TP OFF)"
                       : StringFormat("pad %.2f/%.2f ATR", InpSlBuf + InpStructPad,
                                      InpSlBuf + InpStructPad + InpBreakPad),
      st, gLastBlock));''',
     "panel args")

io.open(P, "w", encoding="utf-8").write(src)
print("\nstage 3 wrote %d bytes" % len(src))


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 4 — two defects in the stage-2 fix itself, found on review
#
#  a) EnsureProtection read prices through `sym`, whose rates are refreshed once
#     per BAR inside EvaluateBar. The guard runs every TICK, so it would compute
#     a clearance from a stale quote. ManageOpenTrade already avoids this by
#     calling SymbolInfoDouble directly; the guard must do the same.
#
#  b) The guard was called from ManageOpenTrade, which OnTick only calls when
#     planActive is true. A position whose plan the EA has lost — restart with a
#     failed adoption, or ClearPlan while the position lingers — is exactly the
#     case the guard exists for, and it was the one case it did not cover.
# ══════════════════════════════════════════════════════════════════════════════
src = io.open(P, encoding="utf-8").read()

sub1('''      double a = (gAtr > 0.0) ? gAtr : (sym.Ask() - sym.Bid()) * 20.0;
      double fallback = isBuy ? entry - a * 1.5 : entry + a * 1.5;
      wantSl = SafeStop(isBuy, isBuy ? sym.Bid() : sym.Ask(),
                        (planActive && planSl > 0.0) ? planSl : fallback);''',
'''      double a = (gAtr > 0.0) ? gAtr : (askNow - bidNow) * 20.0;
      double fallback = isBuy ? entry - a * 1.5 : entry + a * 1.5;
      wantSl = SafeStop(isBuy, isBuy ? bidNow : askNow,
                        (planActive && planSl > 0.0) ? planSl : fallback);''',
     "guard sl rates")

sub1('''      double a = (gAtr > 0.0) ? gAtr : (sym.Ask() - sym.Bid()) * 20.0;
      double fallback = isBuy ? entry + a * InpTp3Atr : entry - a * InpTp3Atr;
      wantTp = SafeTarget(isBuy, isBuy ? sym.Bid() : sym.Ask(),
                          (planActive && planTpSrv > 0.0) ? planTpSrv : fallback);''',
'''      double a = (gAtr > 0.0) ? gAtr : (askNow - bidNow) * 20.0;
      double fallback = isBuy ? entry + a * InpTp3Atr : entry - a * InpTp3Atr;
      wantTp = SafeTarget(isBuy, isBuy ? bidNow : askNow,
                          (planActive && planTpSrv > 0.0) ? planTpSrv : fallback);''',
     "guard tp rates")

sub1('''   bool isBuy   = (pos.PositionType() == POSITION_TYPE_BUY);
   double entry = pos.PriceOpen();
   double haveSl = pos.StopLoss();''',
'''   bool isBuy   = (pos.PositionType() == POSITION_TYPE_BUY);
   double entry = pos.PriceOpen();
   // Live quotes, not sym.* — CSymbolInfo is refreshed once per bar inside
   // EvaluateBar and this runs on every tick.
   double bidNow = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double askNow = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double haveSl = pos.StopLoss();''',
     "guard live quotes")

sub1('''void ManageOpenTrade()
  {
   if(!SelectOwnPosition()) { ClearPlan(); return; }
   EnsureProtection();''',
'''void ManageOpenTrade()
  {
   if(!SelectOwnPosition()) { ClearPlan(); return; }''',
     "guard out of manage")

sub1('''   // Trade management runs on EVERY tick: a target or a stop can be reached
   // mid-bar and waiting for the close would be a different strategy.
   if(planActive) ManageOpenTrade();''',
'''   // v2.5 THE GUARD RUNS FIRST AND UNCONDITIONALLY. It must not be inside the
   // planActive branch: a position whose plan this EA has lost — a restart with
   // a failed adoption, or ClearPlan while the position lingers — is precisely
   // the case where a naked stop-only trade survives, and it was the one case
   // the first version of this guard did not cover.
   EnsureProtection();

   // Trade management runs on EVERY tick: a target or a stop can be reached
   // mid-bar and waiting for the close would be a different strategy.
   if(planActive) ManageOpenTrade();''',
     "guard in ontick")

io.open(P, "w", encoding="utf-8").write(src)
print("\nstage 4 wrote %d bytes" % len(src))
