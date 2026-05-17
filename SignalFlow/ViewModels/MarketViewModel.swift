import Foundation
import Combine

@MainActor
final class MarketViewModel: ObservableObject {

    @Published var btcMetrics = FlowMetrics(symbol: .btcusd)
    @Published var xauMetrics = FlowMetrics(symbol: .xauusd)
    @Published var btcBook: OrderBookSnapshot?
    @Published var btcRecentTrades: [Trade] = []
    @Published var xauRecentTrades: [Trade] = []
    @Published var isConnected: Bool = false

    private let binance = BinanceService()
    private let gold = GoldService()
    let btcEngine = SignalEngine(symbol: .btcusd)
    let xauEngine = SignalEngine(symbol: .xauusd)

    private var bag = Set<AnyCancellable>()
    private let maxRecentTrades = 60

    func start() {
        wireBinance()
        wireGold()
        wireEngines()
        binance.connect()
        gold.start()
        isConnected = true
    }

    func stop() {
        binance.disconnect()
        gold.stop()
        isConnected = false
    }

    private func wireBinance() {
        binance.tradesSubject
            .receive(on: DispatchQueue.main)
            .sink { [weak self] trade in
                guard let self else { return }
                self.btcEngine.ingest(trade: trade)
                self.btcRecentTrades.insert(trade, at: 0)
                if self.btcRecentTrades.count > self.maxRecentTrades {
                    self.btcRecentTrades.removeLast(self.btcRecentTrades.count - self.maxRecentTrades)
                }
            }
            .store(in: &bag)

        binance.bookSubject
            .receive(on: DispatchQueue.main)
            .sink { [weak self] snap in
                guard let self else { return }
                self.btcBook = snap
                self.btcEngine.ingest(book: snap)
            }
            .store(in: &bag)
    }

    private func wireGold() {
        gold.tradesSubject
            .receive(on: DispatchQueue.main)
            .sink { [weak self] trade in
                guard let self else { return }
                self.xauEngine.ingest(trade: trade)
                self.xauRecentTrades.insert(trade, at: 0)
                if self.xauRecentTrades.count > self.maxRecentTrades {
                    self.xauRecentTrades.removeLast(self.xauRecentTrades.count - self.maxRecentTrades)
                }
            }
            .store(in: &bag)
    }

    private func wireEngines() {
        btcEngine.metricsSubject
            .receive(on: DispatchQueue.main)
            .sink { [weak self] m in self?.btcMetrics = m }
            .store(in: &bag)
        xauEngine.metricsSubject
            .receive(on: DispatchQueue.main)
            .sink { [weak self] m in self?.xauMetrics = m }
            .store(in: &bag)
    }

    func metrics(for symbol: Symbol) -> FlowMetrics {
        switch symbol {
        case .btcusd: return btcMetrics
        case .xauusd: return xauMetrics
        }
    }

    func recentTrades(for symbol: Symbol) -> [Trade] {
        switch symbol {
        case .btcusd: return btcRecentTrades
        case .xauusd: return xauRecentTrades
        }
    }
}
