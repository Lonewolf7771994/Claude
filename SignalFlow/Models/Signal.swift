import Foundation

enum SignalSide: String, Codable {
    case buy = "BUY"
    case sell = "SELL"
}

enum SignalStrength: String, Codable {
    case weak, medium, strong

    var emoji: String {
        switch self {
        case .weak: return "•"
        case .medium: return "••"
        case .strong: return "•••"
        }
    }
}

struct TradingSignal: Identifiable, Equatable, Codable {
    let id: UUID
    let symbol: Symbol
    let side: SignalSide
    let strength: SignalStrength
    let price: Double
    let reason: String
    let cvd: Double
    let imbalance: Double
    let momentum: Double
    let timestamp: Date

    init(symbol: Symbol,
         side: SignalSide,
         strength: SignalStrength,
         price: Double,
         reason: String,
         cvd: Double,
         imbalance: Double,
         momentum: Double,
         timestamp: Date = Date()) {
        self.id = UUID()
        self.symbol = symbol
        self.side = side
        self.strength = strength
        self.price = price
        self.reason = reason
        self.cvd = cvd
        self.imbalance = imbalance
        self.momentum = momentum
        self.timestamp = timestamp
    }
}
