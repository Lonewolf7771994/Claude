# SignalFlow

iOS (SwiftUI) app that streams **real** order flow for **BTC/USD** and **XAU/USD**, computes order-flow metrics (CVD, top-of-book imbalance, momentum, aggressor ratio), and surfaces **buy / sell signals** with local push notifications.

## Data feeds

| Symbol  | Source | Stream |
|---------|--------|--------|
| BTC/USD | Binance public WebSocket | `btcusdt@aggTrade` (every print) + `btcusdt@depth20@100ms` (top‑of‑book 20 levels) |
| XAU/USD | Yahoo Finance chart API | `GC=F` 1‑minute ticks (polled every 5s) |

Both feeds are public — no API key required. Network calls go to `stream.binance.com` and `query1.finance.yahoo.com`.

## Signal logic

The `SignalEngine` keeps a rolling 5-minute trade buffer per symbol and recomputes on every print:

- **CVD (1m / 5m)** — cumulative signed notional volume (aggressor side from the maker flag).
- **Book imbalance** — `(bidSize − askSize) / total` across the top 20 levels.
- **Momentum** — price change in basis points over the last 90 s.
- **Aggressor ratio** — buy notional / total notional over 1 m.

A signal fires when **all three** of `CVD 1m`, `book imbalance`, and `momentum` confirm the same direction. Strong vs. medium strength is decided by thresholds in `SignalEngine.swift` (different magnitudes for BTC vs. XAU).

A 45‑second cooldown prevents duplicate alerts. Each signal also fires a local `UNUserNotification`.

## Project layout

```
SignalFlow/
  SignalFlowApp.swift            // @main entry
  Models/
    Trade.swift                  // Symbol enum + Trade struct
    OrderBook.swift              // BookLevel + OrderBookSnapshot
    Signal.swift                 // TradingSignal + side/strength
    FlowMetrics.swift            // live metric snapshot
  Services/
    BinanceService.swift         // WS task for aggTrade + depth, auto‑reconnect
    GoldService.swift            // Yahoo polling for XAU/USD ticks
    SignalEngine.swift           // rolling buffer + signal trigger
    NotificationService.swift    // local UN notifications
  ViewModels/
    MarketViewModel.swift        // wires services → engines → UI
    SignalsViewModel.swift       // signal history + notifications toggle
  Views/
    ContentView.swift            // TabView root
    DashboardView.swift          // both symbols at a glance
    SymbolDetailView.swift       // metrics grid + trade tape
    OrderBookView.swift          // 10‑level depth viz
    SignalsListView.swift        // alert history
    SettingsView.swift           // toggles + stream control
  Resources/
    Info.plist
```

## Build

### Option A — open the included project
```
open SignalFlow.xcodeproj
```
Select an iOS 16+ simulator or device, then **Run**.

### Option B — regenerate with XcodeGen
If you prefer regenerating from spec:
```
brew install xcodegen
xcodegen generate
open SignalFlow.xcodeproj
```

## Disclaimer

Not investment advice. Order‑flow signals are probabilistic; always use risk management.
