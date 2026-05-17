import Foundation
import Combine

/// Polls Yahoo Finance for XAU/USD (GC=F gold futures) tick data.
/// The chart endpoint exposes 1-minute granular ticks publicly.
final class GoldService {

    let tradesSubject = PassthroughSubject<Trade, Never>()
    let priceSubject = PassthroughSubject<Double, Never>()

    private var timer: Timer?
    private var lastSeenTimestamp: TimeInterval = 0
    private var lastPrice: Double = 0
    private let session: URLSession = .shared

    func start() {
        stop()
        fetch()
        timer = Timer.scheduledTimer(withTimeInterval: 5.0, repeats: true) { [weak self] _ in
            self?.fetch()
        }
        RunLoop.main.add(timer!, forMode: .common)
    }

    func stop() {
        timer?.invalidate()
        timer = nil
    }

    private func fetch() {
        var comps = URLComponents(string: "https://query1.finance.yahoo.com/v8/finance/chart/GC=F")!
        comps.queryItems = [
            URLQueryItem(name: "interval", value: "1m"),
            URLQueryItem(name: "range", value: "1d"),
            URLQueryItem(name: "includePrePost", value: "false")
        ]
        guard let url = comps.url else { return }

        var req = URLRequest(url: url)
        req.setValue("Mozilla/5.0 SignalFlow/1.0", forHTTPHeaderField: "User-Agent")

        session.dataTask(with: req) { [weak self] data, _, _ in
            guard let self, let data else { return }
            self.parse(data)
        }.resume()
    }

    private func parse(_ data: Data) {
        guard let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let chart = obj["chart"] as? [String: Any],
              let resultArr = chart["result"] as? [[String: Any]],
              let result = resultArr.first,
              let timestamps = result["timestamp"] as? [Int],
              let indicators = result["indicators"] as? [String: Any],
              let quoteArr = indicators["quote"] as? [[String: Any]],
              let quote = quoteArr.first,
              let closes = quote["close"] as? [Any],
              let volumes = quote["volume"] as? [Any] else { return }

        var newTrades: [Trade] = []
        for i in 0..<timestamps.count {
            let ts = TimeInterval(timestamps[i])
            guard ts > lastSeenTimestamp else { continue }
            guard let price = closes[i] as? Double else { continue }
            let vol = (volumes[i] as? Double) ?? 1.0
            let aggressorBuy = price >= lastPrice
            let isBuyerMaker = !aggressorBuy
            let trade = Trade(symbol: .xauusd,
                              price: price,
                              quantity: max(vol, 1.0),
                              isBuyerMaker: isBuyerMaker,
                              timestamp: Date(timeIntervalSince1970: ts))
            newTrades.append(trade)
            lastPrice = price
            lastSeenTimestamp = ts
        }

        DispatchQueue.main.async {
            for t in newTrades { self.tradesSubject.send(t) }
            if let last = newTrades.last { self.priceSubject.send(last.price) }
        }
    }
}
