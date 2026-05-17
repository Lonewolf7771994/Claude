import Foundation

enum Symbol: String, CaseIterable, Identifiable, Codable {
    case btcusd = "BTC/USD"
    case xauusd = "XAU/USD"

    var id: String { rawValue }

    var binanceStream: String {
        switch self {
        case .btcusd: return "btcusdt"
        case .xauusd: return ""
        }
    }

    var yahooSymbol: String {
        switch self {
        case .btcusd: return "BTC-USD"
        case .xauusd: return "GC=F"
        }
    }

    var displayName: String {
        switch self {
        case .btcusd: return "Bitcoin"
        case .xauusd: return "Gold Spot"
        }
    }

    var tickerColor: String {
        switch self {
        case .btcusd: return "F7931A"
        case .xauusd: return "FFD700"
        }
    }
}

struct Trade: Identifiable, Equatable {
    let id: UUID = UUID()
    let symbol: Symbol
    let price: Double
    let quantity: Double
    let isBuyerMaker: Bool
    let timestamp: Date

    var aggressorIsBuy: Bool { !isBuyerMaker }
    var notional: Double { price * quantity }
}
