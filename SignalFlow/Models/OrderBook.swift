import Foundation

struct BookLevel: Identifiable, Equatable {
    let id = UUID()
    let price: Double
    let size: Double
}

struct OrderBookSnapshot: Equatable {
    let symbol: Symbol
    let bids: [BookLevel]
    let asks: [BookLevel]
    let timestamp: Date

    var bestBid: Double? { bids.first?.price }
    var bestAsk: Double? { asks.first?.price }
    var mid: Double? {
        guard let b = bestBid, let a = bestAsk else { return nil }
        return (b + a) / 2.0
    }

    var spreadBps: Double? {
        guard let b = bestBid, let a = bestAsk, b > 0 else { return nil }
        return (a - b) / b * 10_000.0
    }

    var bidSize: Double { bids.reduce(0) { $0 + $1.size } }
    var askSize: Double { asks.reduce(0) { $0 + $1.size } }

    var imbalance: Double {
        let total = bidSize + askSize
        guard total > 0 else { return 0 }
        return (bidSize - askSize) / total
    }
}
