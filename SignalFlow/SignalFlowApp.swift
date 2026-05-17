import SwiftUI
import UserNotifications

@main
struct SignalFlowApp: App {
    @StateObject private var market = MarketViewModel()
    @StateObject private var signals = SignalsViewModel()

    init() {
        UNUserNotificationCenter.current().requestAuthorization(
            options: [.alert, .sound, .badge]
        ) { _, _ in }
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(market)
                .environmentObject(signals)
                .onAppear {
                    market.start()
                    signals.bind(to: market)
                }
        }
    }
}
