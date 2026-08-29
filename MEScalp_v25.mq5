//+------------------------------------------------------------------+
//|                                                  MEScalp_v25.mq5 |
//|                    © ME Institutional — ME Scalp v2.5 for MT5    |
//+------------------------------------------------------------------+
//
//  A port of the ME Scalp v2.2 TradingView indicator to a MetaTrader 5
//  Expert Advisor. The signal logic is reproduced condition for condition;
//  everything else in this file is the part Pine never has to deal with —
//  order filling modes, stop levels, lot normalisation and partial closes.
//
//  WHAT IS REPRODUCED EXACTLY
//    - Kaufman efficiency-ratio regime gate and leg alignment
//    - five triggers: MSS, FVG retest, liquidity sweep, VWAP band rejection
//      (1σ and 2σ), value-area rejection
//    - session-anchored VWAP with volume-weighted deviation bands
//    - rolling volume profile (POC / VAH / VAL), 100 bars, 24 bins, 70% VA
//    - the 0-5 quality score, including the v2.0 correction that a band
//      trigger does not score its own location
//    - v2.2 STOP PLACEMENT: the stop sits beyond the setup's own invalidation
//      plus a pad, and a setup whose structural stop is too wide is REJECTED
//      rather than squeezed. Targets are ATR distances, decoupled from risk.
//    - breakeven after TP1, the 33/33/34 scale-out, the bar time stop
//
//  WHAT IS DIFFERENT, AND WHY
//    - Bars are evaluated ONCE, on the first tick of a new bar, using the bar
//      that just CLOSED. That is the MT5 equivalent of barstate.isconfirmed
//      and it is what makes the EA's decisions match the indicator's.
//    - MT5 gives no "volume" choice on most FX/CFD feeds, so tick volume is
//      used. The indicator already treats volume as optional; the same
//      degradation applies here — the participation score simply becomes less
//      informative, it does not break.
//    - Pine's plan is a drawing. Here it is three real partial closes, which
//      brokers can refuse for reasons Pine never sees. Those are handled in
//      NormaliseLots() and in the leg-count check inside OpenTrade().
//
//  DEMO ACCOUNTS
//    Nothing here requires a live account. The EA queries the symbol's own
//    filling mode, stops level and lot constraints at init and adapts, which
//    is what usually breaks a ported EA on a demo server with different
//    settings from the one it was written against.
//
//  WHAT IS NOT CLAIMED
//    The outcome statistics in the indicator's header came from synthetic
//    data. Nothing about this port makes them predictions. Run it on the
//    Strategy Tester and on a demo account before it sees real money — the
//    Strategy Tester is the first environment in this whole project capable of
//    producing a real expectancy figure, and it is worth more than every
//    number I have ever quoted you.
//
//  v2.5 — THE TAKE-PROFIT WAS NEVER SENT TO THE BROKER.
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
//  v2.3 — TP1 IS NOW COUNTED, AND THE TWO STOP PADS ARE DECLARED.
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
//  MetaEditor; the logic is what took the work, not the syntax.
//+------------------------------------------------------------------+
#property copyright "ME Institutional"
#property version   "2.50"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>

//============================== INPUTS ==============================
input group "══ Engine ══"
input ENUM_TIMEFRAMES InpTF          = PERIOD_CURRENT; // Timeframe (PERIOD_CURRENT = chart)
input int             InpFreq        = 1;              // Frequency: 0 Selective, 1 Standard, 2 High
input int             InpDir         = 0;              // Direction: 0 Both, 1 Long only, 2 Short only
input int             InpErLen       = 30;             // Regime lookback (bars) - was 20; 30 measured better, 40 gives it back
input bool            InpAlign       = true;           // Only trade WITH the leg in progress

input group "══ Triggers ══"
input bool            InpUseMss      = true;           // MSS - structure break
input bool            InpUseFvg      = true;           // FVG retest
input bool            InpUseSweep    = true;           // Liquidity sweep + reclaim
input bool            InpUseBand     = true;           // VWAP band rejection
input bool            InpUseValue    = true;           // Value-area rejection
input double          InpBandMinW    = 0.30;           // Band must be this wide to count (xATR) - 0 = old behaviour

input group "══ Risk & Targets ══"
input int             InpAtrLen      = 14;             // ATR length
input double          InpStructPad   = 0.25;           // Structure pad beyond invalidation (xATR) - ADDS TO InpSlBuf
input double          InpStructMax   = 4.00;           // Reject setup if structural risk exceeds (xATR)
input double          InpMinRisk     = 0.40;           // Min risk (xATR)
input double          InpSlBuf       = 0.20;           // SL buffer past invalidation (xATR) - ADDS TO InpStructPad; total shown on panel
input double          InpTp1Atr      = 0.80;           // TP1 (xATR)
input double          InpTp2Atr      = 1.40;           // TP2 (xATR)
input double          InpTp3Atr      = 2.00;           // TP3 (xATR)
input int             InpTimeStop    = 12;             // Time stop (bars, 0 = off)
input double          InpBreakPad    = 0.20;           // Extra stop pad for MSS breaks (xATR)
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
input int             InpBrokerTp    = 0;              // Server-side TP: 0 TP3, 1 TP1, 2 off

input group "══ Money & Execution ══"
input double          InpRiskPct     = 0.50;           // Risk per trade (% of balance)
input double          InpFixedLot    = 0.0;            // Fixed lot (0 = use risk %)
input double          InpMaxLot      = 5.0;            // Hard lot cap
input int             InpMaxSpreadPt = 60;             // Max spread to enter (points, 0 = off)
input double          InpMaxSpreadPctRisk = 12.0;      // Refuse trade if spread exceeds this % of the stop (0 = off)
input int             InpSlippagePt  = 30;             // Max deviation (points)
input long            InpMagic       = 22022022;       // Magic number
input int             InpCooldownBar = 3;              // Cooldown between signals (bars)

input group "══ Display ══"
input bool            InpPanel       = true;           // Show status panel

//============================== STATE ===============================
CTrade         trade;
CPositionInfo  pos;
CSymbolInfo    sym;

int      hAtr           = INVALID_HANDLE;
datetime lastBarTime    = 0;
datetime lastSignalBar  = 0;
int      barsSinceEntry = 0;

// live trade bookkeeping (mirrors the indicator's plan object)
bool     planActive  = false;
bool     planIsBuy   = false;
double   planEntry   = 0.0;
double   planSl      = 0.0;
double   planTp1     = 0.0;
double   planTp2     = 0.0;
double   planTp3     = 0.0;
bool     planTp1Done = false;
bool     planTp2Done = false;
bool     planAtBe    = false;
datetime planOpenBar = 0;
string   planTag     = "";

double   gPoc = 0.0, gVah = 0.0, gVal = 0.0;
bool     gProfileOk = false;
double   gVwap = 0.0, gU1 = 0.0, gL1 = 0.0, gU2 = 0.0, gL2 = 0.0;
double   gEr = 0.0;
// v2.5 the last ATR EvaluateBar computed, published so EnsureProtection can
// rebuild a level for a position whose plan the EA no longer holds.
double   gAtr = 0.0;
bool     gLegUp = false, gInTrend = false;
string   gLastBlock = "-";
double   gSpreadShare = 0.0;
// v2.3 TP1 REACH, counted live. gTaken counts plans opened, gTp1Hit counts
// those that reached TP1. The ratio is the reach rate for THIS symbol, THIS
// broker and THIS session, which is worth more than any figure from a
// synthetic generator.
int      gTaken   = 0;
int      gTp1Hit  = 0;
int      gTp2Hit  = 0;
// v2.5 the level actually sitting at the broker, kept so the breakeven modify
// and every re-assert can write it back instead of overwriting it with 0.
double   planTpSrv = 0.0;

#define  VA_LEN   100
#define  VA_BINS   24
#define  FVG_AGE   30
#define  LOOKBACK 320   // bars pulled per evaluation; must exceed VA_LEN + slack

//+------------------------------------------------------------------+
int OnInit()
  {
   if(!sym.Name(_Symbol))
     { Print("ME Scalp: cannot bind symbol ", _Symbol); return(INIT_FAILED); }
   sym.RefreshRates();

   hAtr = iATR(_Symbol, TF(), InpAtrLen);
   if(hAtr == INVALID_HANDLE)
     { Print("ME Scalp: iATR handle failed"); return(INIT_FAILED); }

   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpSlippagePt);
   trade.SetAsyncMode(false);

   // Filling mode is the single most common reason a ported EA does nothing on
   // a demo server: the broker advertises which modes it accepts and rejects
   // anything else with "Unsupported filling mode". Ask, do not assume.
   int fill = (int)SymbolInfoInteger(_Symbol, SYMBOL_FILLING_MODE);
   if((fill & SYMBOL_FILLING_FOK) == SYMBOL_FILLING_FOK)
      trade.SetTypeFilling(ORDER_FILLING_FOK);
   else if((fill & SYMBOL_FILLING_IOC) == SYMBOL_FILLING_IOC)
      trade.SetTypeFilling(ORDER_FILLING_IOC);
   else
      trade.SetTypeFilling(ORDER_FILLING_RETURN);

   PrintFormat("ME Scalp v2.2 | %s %s | digits %d point %.*f | stops %d pt | "
               "lots %.2f-%.2f step %.2f | filling mask %d | %s account",
               _Symbol, EnumToString(TF()), _Digits, _Digits, _Point,
               (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL),
               SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN),
               SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX),
               SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP),
               fill,
               (AccountInfoInteger(ACCOUNT_MARGIN_MODE) == ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)
                  ? "hedging" : "netting");

   if(TF() == PERIOD_M1)
      Print("ME Scalp WARNING: M1. Measured spread cost on XAUUSD is ~25.8% of a "
            "1.5 ATR stop at this timeframe against 11.5% on M5 and 6.7% on M15. "
            "The cost guard will decline most trades here, which is correct.");

   AdoptExistingPosition();
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   if(hAtr != INVALID_HANDLE) IndicatorRelease(hAtr);
   ObjectsDeleteAll(0, "MESC_");
   Comment("");
  }

ENUM_TIMEFRAMES TF()
  { return(InpTF == PERIOD_CURRENT ? (ENUM_TIMEFRAMES)Period() : InpTF); }

//+------------------------------------------------------------------+
void OnTick()
  {
   // v2.5 THE GUARD RUNS FIRST AND UNCONDITIONALLY. It must not be inside the
   // planActive branch: a position whose plan this EA has lost — a restart with
   // a failed adoption, or ClearPlan while the position lingers — is precisely
   // the case where a naked stop-only trade survives, and it was the one case
   // the first version of this guard did not cover.
   EnsureProtection();

   // Trade management runs on EVERY tick: a target or a stop can be reached
   // mid-bar and waiting for the close would be a different strategy.
   if(planActive) ManageOpenTrade();

   if(InpPanel) DrawPanel();

   // Signal evaluation runs ONCE per closed bar. This is the MT5 equivalent
   // of barstate.isconfirmed, and it is what makes the EA agree with the
   // indicator instead of firing on an unfinished bar and revising itself.
   datetime t = iTime(_Symbol, TF(), 0);
   if(t == lastBarTime) return;
   lastBarTime = t;

   if(planActive) { barsSinceEntry++; return; }   // one plan at a time, as in Pine
   EvaluateBar();
  }

//===================== INDICATOR RECONSTRUCTION =====================

// Returns false if history is not deep enough yet — on a fresh chart or a new
// symbol this is normal for the first few minutes.
bool LoadBars(MqlRates &r[])
  {
   ArraySetAsSeries(r, true);
   int got = CopyRates(_Symbol, TF(), 0, LOOKBACK, r);
   return(got >= VA_LEN + InpErLen + 20);
  }

double AtrAt(int shift)
  {
   double b[];
   ArraySetAsSeries(b, true);
   if(CopyBuffer(hAtr, 0, shift, 1, b) < 1) return(0.0);
   return(b[0]);
  }

// Session-anchored VWAP and volume-weighted deviation bands, recomputed from
// the day's bars each time rather than carried in state — a restart, a
// reconnect or a timeframe change then cannot leave a stale accumulator behind.
void ComputeVwap(const MqlRates &r[], int evalShift)
  {
   MqlDateTime d0, dk;
   TimeToStruct(r[evalShift].time, d0);
   double sPV = 0.0, sV = 0.0, sPV2 = 0.0;
   for(int k = ArraySize(r) - 1; k >= evalShift; k--)
     {
      TimeToStruct(r[k].time, dk);
      if(dk.day != d0.day || dk.mon != d0.mon || dk.year != d0.year) continue;
      double tp = (r[k].high + r[k].low + r[k].close) / 3.0;
      double v  = (double)(r[k].tick_volume > 0 ? r[k].tick_volume : 1);
      sPV  += tp * v;
      sV   += v;
      sPV2 += tp * tp * v;
     }
   if(sV <= 0.0) { gVwap = r[evalShift].close; gU1 = gL1 = gU2 = gL2 = gVwap; return; }
   gVwap = sPV / sV;
   double var = MathMax(sPV2 / sV - gVwap * gVwap, 0.0);
   double sd  = MathSqrt(var);
   gU1 = gVwap + sd;  gL1 = gVwap - sd;
   gU2 = gVwap + 2.0 * sd; gL2 = gVwap - 2.0 * sd;
  }

// Rolling volume profile: proportional distribution across overlapped bins,
// then the classic two-bin value-area expansion. Same construction as the
// indicator, so POC/VAH/VAL agree.
void ComputeProfile(const MqlRates &r[], int evalShift)
  {
   gProfileOk = false;
   int last = evalShift + VA_LEN - 1;
   if(last >= ArraySize(r)) return;

   double hi = r[evalShift].high, lo = r[evalShift].low;
   for(int k = evalShift; k <= last; k++)
     { hi = MathMax(hi, r[k].high); lo = MathMin(lo, r[k].low); }
   double binSz = MathMax(hi - lo, _Point) / VA_BINS;

   double acc[VA_BINS];
   ArrayInitialize(acc, 0.0);
   for(int k = evalShift; k <= last; k++)
     {
      double bh = r[k].high, bl = r[k].low;
      double bv = (double)(r[k].tick_volume > 0 ? r[k].tick_volume : 1);
      double br = MathMax(bh - bl, _Point);
      int a0 = (int)MathMax(0, MathMin(VA_BINS - 1, (int)((bl - lo) / binSz)));
      int a1 = (int)MathMax(0, MathMin(VA_BINS - 1, (int)((bh - lo) / binSz)));
      for(int j = a0; j <= a1; j++)
        {
         double bBot = lo + j * binSz, bTop = bBot + binSz;
         double ov = MathMin(bTop, bh) - MathMax(bBot, bl);
         if(ov > 0) acc[j] += bv * (ov / br);
        }
     }

   double total = 0.0;
   for(int j = 0; j < VA_BINS; j++) total += acc[j];
   if(total <= 0.0) return;

   int pb = 0;
   for(int j = 1; j < VA_BINS; j++) if(acc[j] > acc[pb]) pb = j;

   double cur = acc[pb], target = total * 0.70;
   int up = pb, dn = pb;
   for(int it = 0; it < VA_BINS * 2 && cur < target; it++)
     {
      double uv = 0.0, dv = 0.0;
      int us = (int)MathMin(2, VA_BINS - 1 - up);
      int ds = (int)MathMin(2, dn);
      for(int j = up + 1; j <= up + us; j++) uv += acc[j];
      for(int j = dn - ds; j <= dn - 1; j++) dv += acc[j];
      if(us == 0 && ds == 0) break;
      if(us > 0 && (ds == 0 || uv >= dv)) { up += us; cur += uv; }
      else                                { dn -= ds; cur += dv; }
     }
   gPoc = lo + (pb + 0.5) * binSz;
   gVah = lo + (up + 1) * binSz;
   gVal = lo + dn * binSz;
   gProfileOk = true;
  }

// Most recent CONFIRMED pivot. A pivot needs `lr` bars either side, so the
// newest one that can exist relative to the evaluated bar sits lr bars back.
bool LastPivotHigh(const MqlRates &r[], int evalShift, int lr, double &out)
  {
   for(int k = evalShift + lr; k + lr < ArraySize(r); k++)
     {
      bool ok = true;
      for(int j = 1; j <= lr && ok; j++)
         if(r[k].high <= r[k - j].high || r[k].high <= r[k + j].high) ok = false;
      if(ok) { out = r[k].high; return(true); }
     }
   return(false);
  }

bool LastPivotLow(const MqlRates &r[], int evalShift, int lr, double &out)
  {
   for(int k = evalShift + lr; k + lr < ArraySize(r); k++)
     {
      bool ok = true;
      for(int j = 1; j <= lr && ok; j++)
         if(r[k].low >= r[k - j].low || r[k].low >= r[k + j].low) ok = false;
      if(ok) { out = r[k].low; return(true); }
     }
   return(false);
  }

// Newest unfilled FVG that the evaluated bar is retesting. Reconstructed by
// scanning rather than carried in a store: a stateless read cannot drift out
// of sync with the chart after a restart, which a store can.
bool FvgRetestBull(const MqlRates &r[], int evalShift, double atr, double &lvl, double &inv)
  {
   double closePos = ClosePos(r[evalShift]);
   if(closePos < 0.55) return(false);
   for(int k = evalShift + 1; k <= evalShift + FVG_AGE && k + 2 < ArraySize(r); k++)
     {
      double top = r[k].low, bot = r[k + 2].high;      // gap between k and k+2
      if(top - bot < atr * 0.30) continue;
      if(r[k + 1].close <= r[k + 1].open) continue;
      bool filled = false;                              // invalidated since?
      for(int j = evalShift + 1; j < k; j++) if(r[j].close < bot) { filled = true; break; }
      if(filled) continue;
      if(r[evalShift].low <= top && r[evalShift].close >= bot)
        { lvl = top; inv = bot; return(true); }
     }
   return(false);
  }

bool FvgRetestBear(const MqlRates &r[], int evalShift, double atr, double &lvl, double &inv)
  {
   double closePos = ClosePos(r[evalShift]);
   if(closePos > 0.45) return(false);
   for(int k = evalShift + 1; k <= evalShift + FVG_AGE && k + 2 < ArraySize(r); k++)
     {
      double top = r[k + 2].low, bot = r[k].high;
      if(top - bot < atr * 0.30) continue;
      if(r[k + 1].close >= r[k + 1].open) continue;
      bool filled = false;
      for(int j = evalShift + 1; j < k; j++) if(r[j].close > top) { filled = true; break; }
      if(filled) continue;
      if(r[evalShift].high >= bot && r[evalShift].close <= top)
        { lvl = bot; inv = top; return(true); }
     }
   return(false);
  }

double ClosePos(const MqlRates &b)
  {
   double rng = MathMax(b.high - b.low, _Point);
   return((b.close - b.low) / rng);
  }

//========================== SIGNAL LOGIC ============================
void EvaluateBar()
  {
   MqlRates r[];
   if(!LoadBars(r)) { gLastBlock = "history"; return; }

   int s = 1;                                   // the bar that just closed
   double atr = AtrAt(s);
   gAtr = atr;
   if(atr <= 0.0) { gLastBlock = "atr"; return; }

   ComputeVwap(r, s);
   ComputeProfile(r, s);

   // ---- Kaufman efficiency ratio + leg direction ----
   double net = MathAbs(r[s].close - r[s + InpErLen].close);
   double path = 0.0;
   for(int k = s; k < s + InpErLen; k++) path += MathAbs(r[k].close - r[k + 1].close);
   gEr      = (path > 0.0) ? net / path : 0.0;
   gLegUp   = (r[s].close > r[s + InpErLen].close);
   double erMin = (InpFreq == 2) ? 0.25 : (InpFreq == 1) ? 0.32 : 0.40;
   gInTrend = (gEr >= erMin);

   if(!gInTrend) { gLastBlock = "chop"; return; }

   // ---- cooldown ----
   if(lastSignalBar > 0)
     {
      int bars = iBarShift(_Symbol, TF(), lastSignalBar, false);
      if(bars >= 0 && bars < InpCooldownBar) { gLastBlock = "cooldown"; return; }
     }

   // ---- spread guard: a scalp stop is small and spread is a real slice of it
   sym.RefreshRates();
   if(InpMaxSpreadPt > 0)
     {
      long spr = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
      if(spr > InpMaxSpreadPt) { gLastBlock = StringFormat("spread %d", (int)spr); return; }
     }

   double cp   = ClosePos(r[s]);
   double body = MathAbs(r[s].close - r[s].open);
   double relV = RelVolume(r, s);

   double lastPH = 0.0, lastPL = 0.0, sweepHi = 0.0, sweepLo = 0.0;
   bool   hasPH = LastPivotHigh(r, s, 2, lastPH);
   bool   hasPL = LastPivotLow (r, s, 2, lastPL);
   bool   hasSH = LastPivotHigh(r, s, 5, sweepHi);
   bool   hasSL = LastPivotLow (r, s, 5, sweepLo);

   // ---------------- triggers ----------------
   bool mssBull = InpUseMss && hasPH && r[s].close >= lastPH + atr * 0.08 && r[s + 1].close < lastPH;
   bool mssBear = InpUseMss && hasPL && r[s].close <= lastPL - atr * 0.08 && r[s + 1].close > lastPL;

   double fvgBLvl = 0, fvgBInv = 0, fvgSLvl = 0, fvgSInv = 0;
   bool fvgBull = InpUseFvg && FvgRetestBull(r, s, atr, fvgBLvl, fvgBInv);
   bool fvgBear = InpUseFvg && FvgRetestBear(r, s, atr, fvgSLvl, fvgSInv);

   bool swBull = InpUseSweep && hasSL && (sweepLo - r[s].low) >= atr * 0.35 && r[s].close > sweepLo && cp >= 0.55;
   bool swBear = InpUseSweep && hasSH && (r[s].high - sweepHi) >= atr * 0.35 && r[s].close < sweepHi && cp <= 0.45;

   // v2.5 THE BAND MUST HAVE WIDTH. The deviation is accumulated from the
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
   int scoreBear = (relV >= 1.15?1:0) + (body >= atr*0.45?1:0) + (cp <= 0.35?1:0) + (nBear >= 2?1:0) + sLocS;

   bool barBull = r[s].close > r[s].open;
   bool barBear = r[s].close < r[s].open;
   bool allowLong  = (InpDir != 2);
   bool allowShort = (InpDir != 1);

   // ---------------- v2.2 stop placement ----------------
   // Beyond the setup's own invalidation, plus buffer, plus pad. NEVER squeezed
   // into a cap: a setup whose structural stop is genuinely too wide is
   // declined, because squeezing produces a stop that no longer marks
   // invalidation — the defect v2.2 exists to fix.
   // v2.5 MSS takes its own extra clearance. It is the only family stopping
   // beyond a PIVOT rather than a bar extreme, and on 15m that pivot is often a
   // few ticks from the entry: 36% stop-outs against 9% for FVG.
   double pad = atr * InpStructPad;
   double padBull = pad + ((bullName == "MSS") ? atr * InpBreakPad : 0.0);
   double padBear = pad + ((bearName == "MSS") ? atr * InpBreakPad : 0.0);
   double slBull = MathMin(bullInval, r[s].close - atr * InpMinRisk) - atr * InpSlBuf - padBull;
   double slBear = MathMax(bearInval, r[s].close + atr * InpMinRisk) + atr * InpSlBuf + padBear;
   double riskBull = r[s].close - slBull;
   double riskBear = slBear - r[s].close;

   bool riskOkBull = (riskBull >= atr * InpMinRisk * 0.5) && (riskBull <= atr * InpStructMax);
   bool riskOkBear = (riskBear >= atr * InpMinRisk * 0.5) && (riskBear <= atr * InpStructMax);

   bool regimeBuy  = gInTrend && (!InpAlign ||  gLegUp);
   bool regimeSell = gInTrend && (!InpAlign || !gLegUp);

   // ---------------- COST GUARD ----------------
   // A fixed spread cap in points cannot tell you whether a trade is viable,
   // because viability is the spread RELATIVE TO THE STOP, and the stop changes
   // with volatility, session and timeframe. This measures the thing that
   // actually decides it.
   //
   // Measured on XAUUSD, spread as a share of a ~1.5 ATR stop:
   //     1m 25.8%   3m 14.9%   5m 11.5%   15m 6.7%   30m 4.7%
   //
   // Live result that motivated this guard: the same engine cleared its costs
   // on 5m and 15m and did not on 1m. That is not a defect in the signal — it
   // is a quarter of every stop being paid to the spread before the trade
   // starts. No filter setting recovers it, so the trade is declined instead.
   double spreadPx = sym.Ask() - sym.Bid();
   double shareBull = (riskBull > 0.0) ? (spreadPx / riskBull) * 100.0 : 999.0;
   double shareBear = (riskBear > 0.0) ? (spreadPx / riskBear) * 100.0 : 999.0;
   gSpreadShare = MathMin(shareBull, shareBear);
   bool costOkBull = (InpMaxSpreadPctRisk <= 0.0) || (shareBull <= InpMaxSpreadPctRisk);
   bool costOkBear = (InpMaxSpreadPctRisk <= 0.0) || (shareBear <= InpMaxSpreadPctRisk);

   bool buySig  = (nBull>0) && allowLong  && barBull && riskOkBull && costOkBull && scoreBull >= 1 && regimeBuy;
   bool sellSig = (nBear>0) && allowShort && barBear && riskOkBear && costOkBear && scoreBear >= 1 && regimeSell;

   if((nBull > 0 || nBear > 0) && !costOkBull && !costOkBear)
     {
      gLastBlock = StringFormat("cost %.0f%% of stop (cap %.0f%%)",
                                gSpreadShare, InpMaxSpreadPctRisk);
      return;
     }

   if(!buySig && !sellSig)
     {
      gLastBlock = BlockReason(nBull>0, barBull, riskOkBull, scoreBull>=1, regimeBuy,
                               nBear>0, barBear, riskOkBear, scoreBear>=1, regimeSell);
      return;
     }

   bool isBuy = buySig;
   double entry = isBuy ? sym.Ask() : sym.Bid();
   double sl    = isBuy ? slBull : slBear;
   // Targets are ATR distances, deliberately decoupled from risk: a wider stop
   // must not push the targets away too, or the wider stop pays twice.
   double t1 = TpLevel(isBuy, entry, atr, InpTp1Atr, true);
   double t2 = isBuy ? entry + atr*InpTp2Atr : entry - atr*InpTp2Atr;
   double t3 = isBuy ? entry + atr*InpTp3Atr : entry - atr*InpTp3Atr;

   OpenTrade(isBuy, entry, sl, t1, t2, t3, isBuy ? bullName : bearName);
  }

// TP1 is pulled IN to the nearer of the VWAP band, the VWAP itself and the POC
// when one of them sits closer than the ATR distance and is still at least
// 0.6 units away — the same rule the indicator uses.
double TpLevel(bool isBuy, double entry, double unit, double mult, bool snap)
  {
   double d = isBuy ? 1.0 : -1.0;
   double t = entry + d * unit * mult;
   if(!snap) return(t);
   double cands[3];
   cands[0] = isBuy ? gU1 : gL1;
   cands[1] = gVwap;
   cands[2] = gProfileOk ? gPoc : 0.0;
   double best = t;
   for(int i = 0; i < 3; i++)
     {
      double c = cands[i];
      if(c <= 0.0) continue;
      if(((c > entry) != isBuy)) continue;
      if(MathAbs(c - entry) < MathAbs(best - entry) && MathAbs(c - entry) >= unit * 0.6)
         best = c;
     }
   return(best);
  }

double RelVolume(const MqlRates &r[], int s)
  {
   double sum = 0.0;
   int n = 0;
   for(int k = s + 1; k <= s + 20 && k < ArraySize(r); k++) { sum += (double)r[k].tick_volume; n++; }
   if(n == 0 || sum <= 0.0) return(1.0);
   return((double)r[s].tick_volume / (sum / n));
  }

string BlockReason(bool tB,bool dB,bool rB,bool sB,bool gB, bool tS,bool dS,bool rS,bool sS,bool gS)
  {
   string x = "";
   if(tB || tS)
     {
      if(!dB && !dS) x += "bar dir ";
      if(!rB && !rS) x += "risk ";
      if(!sB && !sS) x += "score ";
      if(!gB && !gS) x += "align ";
     }
   return(x == "" ? "-" : x);
  }

//========================== EXECUTION ===============================

// Lot sizing from stop distance. Uses the broker's own tick value rather than
// a hard-coded pip value, so it is correct on gold, FX and indices alike.
double CalcLots(double entry, double sl)
  {
   if(InpFixedLot > 0.0) return(NormaliseLots(InpFixedLot));
   double minL = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxL = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);

   double dist = MathAbs(entry - sl);
   if(dist <= 0.0) return(0.0);

   double tickVal  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickVal <= 0.0 || tickSize <= 0.0) return(NormaliseLots(minL));

   double lossPerLot = (dist / tickSize) * tickVal;
   if(lossPerLot <= 0.0) return(NormaliseLots(minL));

   double budget = AccountInfoDouble(ACCOUNT_BALANCE) * (InpRiskPct / 100.0);
   double lots   = budget / lossPerLot;
   lots = MathMin(lots, InpMaxLot);
   lots = MathMin(lots, maxL);
   return(NormaliseLots(lots));
  }

double NormaliseLots(double v)
  {
   double minL  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxL  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double stepL = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(stepL <= 0.0) stepL = 0.01;
   v = MathFloor(v / stepL) * stepL;
   v = MathMax(minL, MathMin(maxL, v));
   return(NormalizeDouble(v, 2));
  }

// The broker refuses a stop closer than SYMBOL_TRADE_STOPS_LEVEL. Push it out
// rather than dropping it — an unprotected position is worse than a slightly
// wider one, and the reported risk grows to match.
double SafeStop(bool isBuy, double price, double stop)
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
  }

void OpenTrade(bool isBuy, double entry, double sl, double t1, double t2, double t3, string tag)
  {
   sl = SafeStop(isBuy, entry, sl);
   double lots = CalcLots(entry, sl);
   if(lots <= 0.0) { Print("ME Scalp: lot size resolved to zero, skipping"); return; }

   // The scale-out needs three closable pieces. If the position is too small to
   // split three ways at this broker's minimum lot, take fewer legs rather than
   // sending a partial close the server will reject.
   double minL = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   int legs = (lots >= 3.0 * minL) ? 3 : (lots >= 2.0 * minL) ? 2 : 1;

   // v2.5 THE FIX. The fifth argument is the take-profit and it was 0.0 in
   // every build up to v2.3, so the stop was guaranteed by the server and the
   // target was not. A position is now opened with BOTH.
   double refPx = isBuy ? sym.Ask() : sym.Bid();
   double tpSrv = BrokerTp(isBuy, refPx, t1, t3);
   bool ok = isBuy ? trade.Buy(lots, _Symbol, 0.0, sl, tpSrv, "MESC " + tag)
                   : trade.Sell(lots, _Symbol, 0.0, sl, tpSrv, "MESC " + tag);
   if(!ok)
     {
      PrintFormat("ME Scalp: order failed retcode=%d %s", trade.ResultRetcode(),
                  trade.ResultRetcodeDescription());
      return;
     }

   planActive  = true;
   planIsBuy   = isBuy;
   planEntry   = trade.ResultPrice() > 0 ? trade.ResultPrice() : entry;
   planSl      = sl;
   planTp1     = NormalizeDouble(t1, _Digits);
   planTp2     = NormalizeDouble(t2, _Digits);
   planTp3     = NormalizeDouble(t3, _Digits);
   planTp1Done = false;
   planTp2Done = false;
   planAtBe    = false;
   planOpenBar = iTime(_Symbol, TF(), 0);
   planTag     = tag;
   planTpSrv   = tpSrv;
   lastSignalBar  = planOpenBar;
   barsSinceEntry = 0;
   gTaken++;

   PrintFormat("ME Scalp %s %s %.2f lots @ %.*f | SL %.*f | TP %.*f / %.*f / %.*f | server TP %.*f | %d legs",
               isBuy ? "BUY" : "SELL", tag, lots, _Digits, planEntry,
               _Digits, planSl, _Digits, planTp1, _Digits, planTp2, _Digits, planTp3,
               _Digits, planTpSrv, legs);
  }

// v2.5 Re-send the levels the plan says should be on the position. Called after
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
   // Live quotes, not sym.* — CSymbolInfo is refreshed once per bar inside
   // EvaluateBar and this runs on every tick.
   double bidNow = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double askNow = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double haveSl = pos.StopLoss();
   double haveTp = pos.TakeProfit();
   double wantSl = haveSl;
   double wantTp = haveTp;

   if(haveSl <= 0.0)
     {
      // No stop at all. Rebuild one from the plan if we have it, otherwise from
      // ATR, and say so in the log — a naked position is not a normal state.
      double a = (gAtr > 0.0) ? gAtr : (askNow - bidNow) * 20.0;
      double fallback = isBuy ? entry - a * 1.5 : entry + a * 1.5;
      wantSl = SafeStop(isBuy, isBuy ? bidNow : askNow,
                        (planActive && planSl > 0.0) ? planSl : fallback);
      PrintFormat("ME Scalp: position had NO STOP - setting %.*f", _Digits, wantSl);
     }
   if(haveTp <= 0.0 && InpBrokerTp != 2)
     {
      double a = (gAtr > 0.0) ? gAtr : (askNow - bidNow) * 20.0;
      double fallback = isBuy ? entry + a * InpTp3Atr : entry - a * InpTp3Atr;
      wantTp = SafeTarget(isBuy, isBuy ? bidNow : askNow,
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

   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double px  = planIsBuy ? bid : ask;     // the side that pays to exit
   double vol = pos.Volume();
   double minL = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);

   // TP1 — take a third and arm breakeven. Reaching TP1 is what makes the
   // trade unable to lose, which is why v2.2 puts it deliberately close.
   if(!planTp1Done && Reached(px, planTp1))
     {
      planTp1Done = true;
      // v2.3: say it out loud. An unfilled TP1 leg means the position is still
      // carrying full risk, and through v2.2 nothing in the terminal reported
      // how often that was happening.
      gTp1Hit++;
      PrintFormat("ME Scalp TP1 hit @ %.*f | %s %s | TP1 reach %d/%d = %.0f%%",
                  _Digits, px, planIsBuy ? "LONG" : "SHORT", planTag,
                  gTp1Hit, gTaken, gTaken > 0 ? 100.0 * gTp1Hit / gTaken : 0.0);
      if(vol - minL >= minL)
        {
         trade.PositionClosePartial(pos.Ticket(), NormaliseLots(vol / 3.0));
         ReassertLevels();      // some brokers drop SL/TP on a partial close
        }
      if(InpBeAfterTp1 && !planAtBe)
        {
         // v2.5: this used to pass 0.0 as the take-profit, so the breakeven
         // move DELETED the target as well as tightening the stop.
         double be = SafeStop(planIsBuy, px, planEntry);
         if(trade.PositionModify(pos.Ticket(), be, planTpSrv)) { planSl = be; planAtBe = true; }
        }
      return;
     }
   if(planTp1Done && !planTp2Done && Reached(px, planTp2))
     {
      planTp2Done = true;
      gTp2Hit++;
      PrintFormat("ME Scalp TP2 hit @ %.*f | %s %s | TP2 reach %d/%d = %.0f%%",
                  _Digits, px, planIsBuy ? "LONG" : "SHORT", planTag,
                  gTp2Hit, gTaken, gTaken > 0 ? 100.0 * gTp2Hit / gTaken : 0.0);
      if(vol - minL >= minL)
        {
         trade.PositionClosePartial(pos.Ticket(), NormaliseLots(vol / 2.0));
         ReassertLevels();
        }
      return;
     }
   if(planTp2Done && Reached(px, planTp3))
     { trade.PositionClose(pos.Ticket()); ClearPlan(); return; }

   // Time stop — a backstop, not the main exit. Few trades reach it.
   if(InpTimeStop > 0 && barsSinceEntry >= InpTimeStop)
     {
      Print("ME Scalp: time stop");
      trade.PositionClose(pos.Ticket());
      ClearPlan();
     }
  }

void DrawPanel()
  {
   static datetime lastDraw = 0;
   if(TimeCurrent() == lastDraw) return;          // once per second is plenty
   lastDraw = TimeCurrent();
   string st = planActive
      ? StringFormat("%s %s | %d bars | %s",
                     planIsBuy ? "LONG" : "SHORT", planTag, barsSinceEntry,
                     planAtBe ? "SL@BE" : "SL live")
      : "flat";
   Comment(StringFormat(
      "ME Scalp v2.5  %s %s\n"
      "regime   %s  ER %.2f (need %.2f)\n"
      "VWAP     %.*f   band +-1s %.*f / %.*f\n"
      "profile  %s\n"
      "spread   %d pt  =  %.0f%% of stop (cap %.0f%%)\n"
      "TP1/TP2  %s\n"
      "server   SL %.*f   TP %.*f   %s\n"
      "trade    %s\n"
      "last     %s",
      _Symbol, EnumToString(TF()),
      gInTrend ? (gLegUp ? "TREND up" : "TREND down") : "CHOP",
      gEr, (InpFreq == 2) ? 0.25 : (InpFreq == 1) ? 0.32 : 0.40,
      _Digits, gVwap, _Digits, gU1, _Digits, gL1,
      gProfileOk ? StringFormat("POC %.*f  VAH %.*f  VAL %.*f",
                                _Digits, gPoc, _Digits, gVah, _Digits, gVal)
                 : "building",
      (int)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD), gSpreadShare, InpMaxSpreadPctRisk,
      gTaken > 0 ? StringFormat("reach %.0f%% / %.0f%%   (%d, %d of %d)",
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
      st, gLastBlock));
  }

bool Reached(double px, double level)
  { return(planIsBuy ? (px >= level) : (px <= level)); }

bool SelectOwnPosition()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
      if(pos.SelectByIndex(i))
         if(pos.Symbol() == _Symbol && pos.Magic() == InpMagic) return(true);
   return(false);
  }

void ClearPlan()
  {
   planActive = false; planTp1Done = false; planTp2Done = false; planAtBe = false;
   planTpSrv  = 0.0;
   barsSinceEntry = 0;
  }

// If the EA is reattached while one of its positions is open, adopt it rather
// than opening a second one alongside it.
void AdoptExistingPosition()
  {
   if(!SelectOwnPosition()) return;
   planActive  = true;
   planIsBuy   = (pos.PositionType() == POSITION_TYPE_BUY);
   planEntry   = pos.PriceOpen();
   planSl      = pos.StopLoss();
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
   barsSinceEntry = 0;
  }
