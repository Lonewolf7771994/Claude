import Foundation
import Combine

/// Streams BTC/USDT trades and depth from Binance's public WebSocket.
/// Docs: https://binance-docs.github.io/apidocs/spot/en/#websocket-market-streams
final class BinanceService: NSObject {

    let tradesSubject = PassthroughSubject<Trade, Never>()
    let bookSubject = PassthroughSubject<OrderBookSnapshot, Never>()

    private var session: URLSession!
    private var trades: URLSessionWebSocketTask?
    private var depth: URLSessionWebSocketTask?
    private var reconnectAttempt = 0
    private let queue = DispatchQueue(label: "binance.ws", qos: .userInitiated)

    override init() {
        super.init()
        let config = URLSessionConfiguration.default
        config.waitsForConnectivity = true
        self.session = URLSession(configuration: config,
                                  delegate: self,
                                  delegateQueue: nil)
    }

    func connect() {
        connectTrades()
        connectDepth()
    }

    func disconnect() {
        trades?.cancel(with: .goingAway, reason: nil)
        depth?.cancel(with: .goingAway, reason: nil)
        trades = nil
        depth = nil
    }

    // MARK: - Trades

    private func connectTrades() {
        let url = URL(string: "wss://stream.binance.com:9443/ws/btcusdt@aggTrade")!
        let task = session.webSocketTask(with: url)
        trades = task
        task.resume()
        listen(on: task, parser: parseTrade) { [weak self] in
            self?.reconnect(.trades)
        }
    }

    // MARK: - Depth

    private func connectDepth() {
        let url = URL(string: "wss://stream.binance.com:9443/ws/btcusdt@depth20@100ms")!
        let task = session.webSocketTask(with: url)
        depth = task
        task.resume()
        listen(on: task, parser: parseDepth) { [weak self] in
            self?.reconnect(.depth)
        }
    }

    private enum Stream { case trades, depth }

    private func reconnect(_ stream: Stream) {
        reconnectAttempt += 1
        let delay = min(pow(2.0, Double(reconnectAttempt)), 30.0)
        queue.asyncAfter(deadline: .now() + delay) { [weak self] in
            guard let self else { return }
            switch stream {
            case .trades: self.connectTrades()
            case .depth: self.connectDepth()
            }
        }
    }

    private func listen(on task: URLSessionWebSocketTask,
                        parser: @escaping (Data) -> Void,
                        onClose: @escaping () -> Void) {
        task.receive { [weak self] result in
            guard let self else { return }
            switch result {
            case .failure:
                onClose()
                return
            case .success(let message):
                switch message {
                case .data(let data):
                    parser(data)
                case .string(let text):
                    if let data = text.data(using: .utf8) { parser(data) }
                @unknown default:
                    break
                }
                self.listen(on: task, parser: parser, onClose: onClose)
            }
        }
    }

    private func parseTrade(_ data: Data) {
        guard let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let priceStr = obj["p"] as? String, let price = Double(priceStr),
              let qtyStr = obj["q"] as? String, let qty = Double(qtyStr),
              let isBuyerMaker = obj["m"] as? Bool,
              let tsMs = obj["T"] as? Int else { return }

        let trade = Trade(symbol: .btcusd,
                          price: price,
                          quantity: qty,
                          isBuyerMaker: isBuyerMaker,
                          timestamp: Date(timeIntervalSince1970: TimeInterval(tsMs) / 1000.0))
        DispatchQueue.main.async {
            self.tradesSubject.send(trade)
        }
        reconnectAttempt = 0
    }

    private func parseDepth(_ data: Data) {
        guard let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let bidsArr = obj["bids"] as? [[String]],
              let asksArr = obj["asks"] as? [[String]] else { return }

        let bids: [BookLevel] = bidsArr.compactMap {
            guard $0.count >= 2, let p = Double($0[0]), let s = Double($0[1]) else { return nil }
            return BookLevel(price: p, size: s)
        }
        let asks: [BookLevel] = asksArr.compactMap {
            guard $0.count >= 2, let p = Double($0[0]), let s = Double($0[1]) else { return nil }
            return BookLevel(price: p, size: s)
        }
        let snap = OrderBookSnapshot(symbol: .btcusd,
                                     bids: bids,
                                     asks: asks,
                                     timestamp: Date())
        DispatchQueue.main.async {
            self.bookSubject.send(snap)
        }
    }
}

extension BinanceService: URLSessionDelegate, URLSessionWebSocketDelegate {}
