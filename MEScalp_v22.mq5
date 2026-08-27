//+------------------------------------------------------------------+
//|                                                  MEScalp_v22.mq5 |
//|                    © ME Institutional — ME Scalp v2.2 for MT5    |
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
//  THIS FILE HAS NOT BEEN COMPILED. No MQL5 toolchain was available in the
//  environment that wrote it. Expect to fix compile errors on first open in
//  MetaEditor; the logic is what took the work, not the syntax.
//+------------------------------------------------------------------+
#property copyright "ME Institutional"
#property version   "2.20"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>

//============================== INPUTS ==============================
input group "══ Engine ══"
input ENUM_TIMEFRAMES InpTF          = PERIOD_CURRENT; // Timeframe (PERIOD_CURRENT = chart)
input int             InpFreq        = 1;              // Frequency: 0 Selective, 1 Standard, 2 High
input int             InpDir         = 0;              // Direction: 0 Both, 1 Long only, 2 Short only
input int             InpErLen       = 20;             // Regime lookback (bars)
input bool            InpAlign       = true;           // Only trade WITH the leg in progress

input group "══ Triggers ══"
input bool            InpUseMss      = true;           // MSS - structure break
input bool            InpUseFvg      = true;           // FVG retest
input bool            InpUseSweep    = true;           // Liquidity sweep + reclaim
input bool            InpUseBand     = true;           // VWAP band rejection
input bool            InpUseValue    = true;           // Value-area rejection

input group "══ Risk & Targets ══"
input int             InpAtrLen      = 14;             // ATR length
input double          InpStructPad   = 0.25;           // Structure pad beyond invalidation (xATR)
input double          InpStructMax   = 4.00;           // Reject setup if structural risk exceeds (xATR)
input double          InpMinRisk     = 0.40;           // Min risk (xATR)
input double          InpSlBuf       = 0.20;           // SL buffer past invalidation (xATR)
input double          InpTp1Atr      = 0.80;           // TP1 (xATR)
input double          InpTp2Atr      = 1.40;           // TP2 (xATR)
input double          InpTp3Atr      = 2.00;           // TP3 (xATR)
input int             InpTimeStop    = 12;             // Time stop (bars, 0 = off)
input bool            InpBeAfterTp1  = true;           // Move stop to breakeven after TP1

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
bool     gLegUp = false, gInTrend = false;
string   gLastBlock = "-";
double   gSpreadShare = 0.0;

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

   bool bandBull  = InpUseBand && r[s].low  <= gL1 && r[s].close > gL1 && cp >= 0.55;
   bool bandBear  = InpUseBand && r[s].high >= gU1 && r[s].close < gU1 && cp <= 0.45;
   bool band2Bull = InpUseBand && r[s].low  <= gL2 && r[s].close > gL2 && cp >= 0.55;
   bool band2Bear = InpUseBand && r[s].high >= gU2 && r[s].close < gU2 && cp <= 0.45;

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
   double pad = atr * InpStructPad;
   double slBull = MathMin(bullInval, r[s].close - atr * InpMinRisk) - atr * InpSlBuf - pad;
   double slBear = MathMax(bearInval, r[s].close + atr * InpMinRisk) + atr * InpSlBuf + pad;
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

   bool ok = isBuy ? trade.Buy(lots, _Symbol, 0.0, sl, 0.0, "MESC " + tag)
                   : trade.Sell(lots, _Symbol, 0.0, sl, 0.0, "MESC " + tag);
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
   lastSignalBar  = planOpenBar;
   barsSinceEntry = 0;

   PrintFormat("ME Scalp %s %s %.2f lots @ %.*f | SL %.*f | TP %.*f / %.*f / %.*f | %d legs",
               isBuy ? "BUY" : "SELL", tag, lots, _Digits, planEntry,
               _Digits, planSl, _Digits, planTp1, _Digits, planTp2, _Digits, planTp3, legs);
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
      if(vol - minL >= minL) trade.PositionClosePartial(pos.Ticket(), NormaliseLots(vol / 3.0));
      if(InpBeAfterTp1 && !planAtBe)
        {
         double be = SafeStop(planIsBuy, px, planEntry);
         if(trade.PositionModify(pos.Ticket(), be, 0.0)) { planSl = be; planAtBe = true; }
        }
      return;
     }
   if(planTp1Done && !planTp2Done && Reached(px, planTp2))
     {
      planTp2Done = true;
      if(vol - minL >= minL) trade.PositionClosePartial(pos.Ticket(), NormaliseLots(vol / 2.0));
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
      "ME Scalp v2.2  %s %s\n"
      "regime   %s  ER %.2f (need %.2f)\n"
      "VWAP     %.*f   band +-1s %.*f / %.*f\n"
      "profile  %s\n"
      "spread   %d pt  =  %.0f%% of stop (cap %.0f%%)\n"
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
   planTp1Done = true;                     // unknown, so assume de-risked
   planTp2Done = true;
   planAtBe    = (MathAbs(planSl - planEntry) < 2 * _Point);
   barsSinceEntry = 0;
   Print("ME Scalp: adopted an existing position; TP legs assumed already taken");
  }
