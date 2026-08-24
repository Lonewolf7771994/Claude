"""v4.3 header."""
import io, sys

P = "/home/user/Claude/MovementEnginePro.v4.3.pine"
src = io.open(P, encoding="utf-8").read()

anchor = """// ═══════════════════════════════════════════════════════════════════════════════
// v4.2 — SLOW, FRAGMENTED, MISTAKEN. THREE COMPLAINTS, THREE DIFFERENT CAUSES."""

head = """// ═══════════════════════════════════════════════════════════════════════════════
// v4.3 — VOLUME PROFILE, ORDER FLOW, AND NO REVERSAL TRADES
// ─────────────────────────────────────────────────────────────────────────────
// THE REQUEST: signals should read the volume profile and order flow, use the
// zones, and take no reversal trades.
//
// The last part conflicts with how this engine gets most of its trades, so that
// is measured first and reported before anything is claimed for it.
//
// ─────────────────────────────────────────────────────────────────────────────
// NO REVERSAL — WHAT IT COSTS.
//
// Two of the five triggers are REVERSAL SETUPS BY CONSTRUCTION, and they are the
// two that supply most of the raw material. v4.0's own header calls a band
// rejection "a REVERSION setup" and hands it the VWAP mean as its first target
// for exactly that reason. Measured, 15m, 150 days x 6 seeds, reversal defined
// as the trade fighting price over the last 20 bars:
//
//     trigger   events/day   reversal   survives/day
//     band          28.38        43%          16.22
//     band2         23.28        54%          10.80
//     sweep          4.31        35%           2.80
//     mss            4.23         7%           3.91
//     fvg            1.75        13%           1.53
//     ALL           70.65        45%          39.18
//
// The gate removes 45% of raw trigger supply, and MSS and FVG barely notice —
// they are continuation setups already. The band triggers pay nearly the whole
// bill.
//
// THE TRIGGER SHAPE WAS NEVER THE PROBLEM. A bull sweep taken while the leg is
// DOWN is a reversal; the identical sweep taken while the leg is UP is a
// pullback that resumed. What decided which one you got was an EXEMPTION:
// v3.5.1 excused sweeps from the CVD and momentum gates precisely because "the
// trend reads bearish at exactly the moment the setup forms", and v4.0 extended
// it to bands. That exemption is the mechanism, so under this gate it is
// withdrawn — and only under this gate, since without it those triggers cannot
// fire at all, which is the v3.5.1 defect re-created.
//
// ─────────────────────────────────────────────────────────────────────────────
// WHAT NO-REVERSAL BUYS, AND WHY THIS FILE WILL NOT CLAIM IT BUYS ANYTHING.
//
// Splitting the SAME triggers with the SAME stop and the SAME ladder:
//
//                    trades    TP1   TP2   TP3    SL    BE  bars
//     continuation    16884    61%   26%   12%   39%   53%     4
//     reversal        16473    62%   20%    9%   38%   55%     5
//
// The stop-out rate is IDENTICAL — 39% against 38%, with reversal marginally
// ahead. Continuation reaches the deeper targets more often and resolves a bar
// sooner, and that is the entire difference.
//
// THAT IS NOT EVIDENCE AGAINST THE FILTER, AND IT MUST NOT BE READ AS SUCH. The
// generator's trend_k is CALIBRATED so a naive momentum rule earns nothing above
// the driftless case — gen.py says so in terms, and says the original 0.55 was
// "a disaster" that paid trend-following +0.214R and produced a fake +0.29R
// discovery. A harness tuned until trend-following is worth zero cannot evaluate
// a trend-alignment filter. It will return flat by construction, and it did.
//
// So: the 45% supply cost is a COUNT and is real. The benefit is UNMEASURED and
// unmeasurable here. Trading only with the leg is a legitimate preference and it
// is now available; it is not a demonstrated improvement and this header will
// not pretend otherwise.
//
// WHAT THE SAME TABLE DOES SAY, strongly, is that the TRIGGER matters far more
// than the direction. Stop-out rate by trigger, with the leg:
//
//     fvg 19%   sweep 30%   band 39%   mss 47%   value 51%
//
// A spread of 19% to 51% dwarfs the 39%-versus-38% the reversal question turns
// on. If you want fewer losing trades, that column is where to look.
//
// ─────────────────────────────────────────────────────────────────────────────
// VOLUME PROFILE — it now starts trades instead of only decorating them.
//
// POC RECLAIM, new trigger. The POC is the highest-volume price in the profile,
// the price the most business was done at. Through v4.2 the engine computed it
// every single bar and let it do NOTHING — drawn, published in the alert,
// offered as a target candidate, never once an entry. Closing through it from
// the other side is the profile's centre of gravity changing hands. Measured at
// 7.81 events/day on 15m, of which 6.31 run with the leg — about a fifth of what
// the no-reversal gate removes, handed back.
//
// VALUE-AREA MIGRATION, and this one is a bug fix. frvpBullOk was
// `close >= VAL` and frvpBearOk was `close <= VAH`, so BOTH WERE TRUE while
// price sat inside the value area — most of the time. A confluence leg that
// scores for the bull side and the bear side simultaneously is not a directional
// reading, and it fed the confluence gate AND the invalidation exit. v3.5.23
// recorded the symptom without naming it: "a fully flipped market commonly reads
// 3/3 against and 1/3 for". The 1/3 was this leg scoring for the losing side.
// Replaced by whether the value area ITSELF has moved, which has one answer.
//
// ─────────────────────────────────────────────────────────────────────────────
// ORDER FLOW — a reading that is not the shape of one candle.
//
// ABSORPTION: heavy participation producing almost no range. Every other
// order-flow test here reads the SHAPE of a single bar — close position, body
// conviction, wick ratio — and shape cannot distinguish a quiet bar from one
// where a large participant is being filled into. Effort against result can.
// Measured at 4.85 events/day on 15m, added as a sixth confluence reading so it
// can corroborate a setup without being able to manufacture one. A sixth reading
// also makes each mode's threshold slightly easier to reach, which deliberately
// offsets a little of what the no-reversal gate takes away.
//
// ─────────────────────────────────────────────────────────────────────────────
// TURNING IT OFF. i_noReversal off restores v4.2's gating exactly, including the
// counter-trend exemption. i_pocTrig and i_vaMigrate are separate toggles, so
// the profile work can be kept or dropped independently of the direction rule.
// ═══════════════════════════════════════════════════════════════════════════════

"""

if src.count(anchor) != 1:
    sys.exit("anchor not unique")
src = src.replace(anchor, head + anchor)
io.open(P, "w", encoding="utf-8").write(src)
print("ok  header — wrote %d bytes" % len(src))
