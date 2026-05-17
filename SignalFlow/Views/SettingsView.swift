import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var signals: SignalsViewModel
    @EnvironmentObject var market: MarketViewModel

    var body: some View {
        NavigationStack {
            Form {
                Section("Notifications") {
                    Toggle("Push signal alerts", isOn: $signals.notificationsEnabled)
                }

                Section("Streams") {
                    LabeledContent("BTC/USD", value: "Binance aggTrade + depth20")
                    LabeledContent("XAU/USD", value: "Yahoo Finance GC=F 1m")
                    Button(market.isConnected ? "Stop streaming" : "Start streaming") {
                        market.isConnected ? market.stop() : market.start()
                    }
                    .foregroundStyle(market.isConnected ? .red : .green)
                }

                Section("Strategy") {
                    Text("Signals trigger when 1-minute volume delta, top-of-book imbalance and short-term momentum confirm the same direction.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }

                Section("Disclaimer") {
                    Text("Not investment advice. Order-flow signals are probabilistic. Always trade with proper risk management.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            }
            .navigationTitle("Settings")
        }
    }
}
