import Foundation
import Combine

/// Consumes the trade stream for a symbol, computes order-flow metrics, and
/// emits BUY/SELL signals when delta + imbalance + momentum align.
final class SignalEngine {

    let symbol: Symbol
    let signalSubject = PassthroughSubject<TradingSignal, Never>()
    let metricsSubject: CurrentValueSubject<FlowMetrics, Never>

    private var recentTrades: [Trade] = []
    private var lastBookImbalance: Double = 0
    private var lastSpreadBps: Double = 0
    private var lastSignalAt: Date = .distantPast
    private let cooldown: TimeInterval = 45

    private let largePrintThreshold: Double
    private let cvdTriggerStrong: Double
    private let cvdTriggerMedium: Double

    init(symbol: Symbol) {
        self.symbol = symbol
        self.metricsSubject = CurrentValueSubject(FlowMetrics(symbol: symbol))
        switch symbol {
        case .btcusd:
            self.largePrintThreshold = 250_000
            self.cvdTriggerStrong = 800_000
            self.cvdTriggerMedium = 300_000
        case .xauusd:
            self.largePrintThreshold = 50
            self.cvdTriggerStrong = 600
            self.cvdTriggerMedium = 200
        }
    }

    func ingest(book: OrderBookSnapshot) {
        lastBookImbalance = book.imbalance
        lastSpreadBps = book.spreadBps ?? 0
        recompute()
    }

    func ingest(trade: Trade) {
        recentTrades.append(trade)
        let cutoff = Date().addingTimeInterval(-5 * 60)
        if recentTrades.first?.timestamp ?? cutoff < cutoff {
            recentTrades.removeAll { $0.timestamp < cutoff }
        }
        recompute()
        evaluateSignal()
    }

    private func recompute() {
        let now = Date()
        let cutoff1m = now.addingTimeInterval(-60)
        let cutoff5m = now.addingTimeInterval(-300)
        let cutoffMomentum = now.addingTimeInterval(-90)

        var buy1m: Double = 0
        var sell1m: Double = 0
        var delta5m: Double = 0
        var cvd: Double = 0
        var large: Int = 0
        var firstPriceInWindow: Double?

        for t in recentTrades {
            let signed = t.aggressorIsBuy ? t.notional : -t.notional
            cvd += signed
            if t.timestamp >= cutoff5m { delta5m += signed }
            if t.timestamp >= cutoff1m {
                if t.aggressorIsBuy { buy1m += t.notional } else { sell1m += t.notional }
                if t.notional >= largePrintThreshold { large += 1 }
            }
            if t.timestamp >= cutoffMomentum, firstPriceInWindow == nil {
                firstPriceInWindow = t.price
            }
        }

        let lastPrice = recentTrades.last?.price ?? metricsSubject.value.lastPrice
        let momentum: Double = {
            guard let first = firstPriceInWindow, first > 0 else { return 0 }
            return (lastPrice - first) / first * 10_000.0
        }()

        let total = buy1m + sell1m
        let aggressor = total > 0 ? buy1m / total : 0.5

        var m = FlowMetrics(symbol: symbol)
        m.lastPrice = lastPrice
        m.cvd = cvd
        m.cvd1m = buy1m - sell1m
        m.cvd5m = delta5m
        m.buyVolume1m = buy1m
        m.sellVolume1m = sell1m
        m.imbalance = lastBookImbalance
        m.spreadBps = lastSpreadBps
        m.momentum1m = momentum
        m.largePrintCount = large
        m.aggressorRatio = aggressor
        m.updatedAt = now

        metricsSubject.send(m)
    }

    private func evaluateSignal() {
        let m = metricsSubject.value
        guard Date().timeIntervalSince(lastSignalAt) > cooldown else { return }
        guard m.lastPrice > 0 else { return }
        guard m.totalVolume1m > 0 else { return }

        let strongBuy = m.cvd1m >= cvdTriggerStrong
            && m.imbalance > 0.15
            && m.momentum1m > 2.0
            && m.aggressorRatio > 0.6
        let mediumBuy = m.cvd1m >= cvdTriggerMedium
            && m.imbalance > 0.08
            && m.momentum1m > 0.5
        let strongSell = m.cvd1m <= -cvdTriggerStrong
            && m.imbalance < -0.15
            && m.momentum1m < -2.0
            && m.aggressorRatio < 0.4
        let mediumSell = m.cvd1m <= -cvdTriggerMedium
            && m.imbalance < -0.08
            && m.momentum1m < -0.5

        let side: SignalSide
        let strength: SignalStrength
        let reason: String

        if strongBuy {
            side = .buy
            strength = .strong
            reason = "Aggressive bid sweep, book bid-heavy, upside momentum"
        } else if strongSell {
            side = .sell
            strength = .strong
            reason = "Aggressive ask hits, book ask-heavy, downside momentum"
        } else if mediumBuy {
            side = .buy
            strength = .medium
            reason = "Net buy delta with positive book imbalance"
        } else if mediumSell {
            side = .sell
            strength = .medium
            reason = "Net sell delta with negative book imbalance"
        } else {
            return
        }

        let signal = TradingSignal(symbol: symbol,
                                   side: side,
                                   strength: strength,
                                   price: m.lastPrice,
                                   reason: reason,
                                   cvd: m.cvd1m,
                                   imbalance: m.imbalance,
                                   momentum: m.momentum1m)
        lastSignalAt = Date()
        signalSubject.send(signal)
    }
}
