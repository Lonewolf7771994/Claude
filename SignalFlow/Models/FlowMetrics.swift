import Foundation

struct FlowMetrics: Equatable {
    var symbol: Symbol
    var lastPrice: Double = 0
    var cvd: Double = 0
    var cvd1m: Double = 0
    var cvd5m: Double = 0
    var buyVolume1m: Double = 0
    var sellVolume1m: Double = 0
    var imbalance: Double = 0
    var spreadBps: Double = 0
    var momentum1m: Double = 0
    var largePrintCount: Int = 0
    var aggressorRatio: Double = 0.5
    var updatedAt: Date = Date()

    var delta1m: Double { buyVolume1m - sellVolume1m }
    var totalVolume1m: Double { buyVolume1m + sellVolume1m }
}
