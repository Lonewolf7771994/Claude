import Foundation
import Combine

@MainActor
final class SignalsViewModel: ObservableObject {

    @Published private(set) var signals: [TradingSignal] = []
    @Published var notificationsEnabled: Bool = true

    private var bag = Set<AnyCancellable>()
    private let maxStored = 200

    func bind(to market: MarketViewModel) {
        market.btcEngine.signalSubject
            .receive(on: DispatchQueue.main)
            .sink { [weak self] signal in self?.add(signal) }
            .store(in: &bag)

        market.xauEngine.signalSubject
            .receive(on: DispatchQueue.main)
            .sink { [weak self] signal in self?.add(signal) }
            .store(in: &bag)
    }

    private func add(_ signal: TradingSignal) {
        signals.insert(signal, at: 0)
        if signals.count > maxStored {
            signals.removeLast(signals.count - maxStored)
        }
        if notificationsEnabled {
            NotificationService.send(signal)
        }
    }

    func clear() { signals.removeAll() }
}
