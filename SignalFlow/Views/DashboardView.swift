import SwiftUI

struct DashboardView: View {
    @EnvironmentObject var market: MarketViewModel

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    ConnectionBar(connected: market.isConnected)
                    ForEach(Symbol.allCases) { symbol in
                        NavigationLink {
                            SymbolDetailView(symbol: symbol)
                        } label: {
                            SymbolCard(symbol: symbol,
                                       metrics: market.metrics(for: symbol))
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding()
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("SignalFlow")
        }
    }
}

private struct ConnectionBar: View {
    let connected: Bool
    var body: some View {
        HStack(spacing: 8) {
            Circle()
                .fill(connected ? Color.green : Color.red)
                .frame(width: 8, height: 8)
            Text(connected ? "Live order flow streaming" : "Disconnected")
                .font(.footnote)
                .foregroundStyle(.secondary)
            Spacer()
        }
    }
}

private struct SymbolCard: View {
    let symbol: Symbol
    let metrics: FlowMetrics

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text(symbol.rawValue)
                        .font(.title2.bold())
                    Text(symbol.displayName)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Text(format(price: metrics.lastPrice, symbol: symbol))
                    .font(.title2.monospacedDigit().bold())
            }

            HStack(spacing: 12) {
                StatChip(title: "CVD 1m",
                         value: signed(metrics.cvd1m),
                         tint: metrics.cvd1m >= 0 ? .green : .red)
                StatChip(title: "Imbalance",
                         value: percent(metrics.imbalance),
                         tint: metrics.imbalance >= 0 ? .green : .red)
                StatChip(title: "Mom bps",
                         value: signedNumber(metrics.momentum1m),
                         tint: metrics.momentum1m >= 0 ? .green : .red)
            }

            DeltaBar(buy: metrics.buyVolume1m, sell: metrics.sellVolume1m)
        }
        .padding()
        .background(RoundedRectangle(cornerRadius: 16).fill(Color(.secondarySystemGroupedBackground)))
    }

    private func format(price: Double, symbol: Symbol) -> String {
        guard price > 0 else { return "—" }
        switch symbol {
        case .btcusd: return String(format: "$%,.2f", price)
        case .xauusd: return String(format: "$%,.2f", price)
        }
    }

    private func signed(_ v: Double) -> String {
        let abs = formatAbbreviated(value: Swift.abs(v))
        return (v >= 0 ? "+" : "−") + abs
    }

    private func signedNumber(_ v: Double) -> String {
        String(format: "%+.1f", v)
    }

    private func percent(_ v: Double) -> String {
        String(format: "%+.1f%%", v * 100)
    }

    private func formatAbbreviated(value: Double) -> String {
        switch value {
        case 1_000_000...:
            return String(format: "$%.2fM", value / 1_000_000)
        case 1_000...:
            return String(format: "$%.1fK", value / 1_000)
        default:
            return String(format: "$%.0f", value)
        }
    }
}

private struct StatChip: View {
    let title: String
    let value: String
    let tint: Color
    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(title)
                .font(.caption2)
                .foregroundStyle(.secondary)
            Text(value)
                .font(.subheadline.monospacedDigit().bold())
                .foregroundStyle(tint)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(8)
        .background(RoundedRectangle(cornerRadius: 8).fill(tint.opacity(0.1)))
    }
}

private struct DeltaBar: View {
    let buy: Double
    let sell: Double
    var body: some View {
        let total = max(buy + sell, 1)
        let buyRatio = buy / total
        return VStack(alignment: .leading, spacing: 4) {
            Text("1m volume split")
                .font(.caption2)
                .foregroundStyle(.secondary)
            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    RoundedRectangle(cornerRadius: 4)
                        .fill(Color.red.opacity(0.6))
                    RoundedRectangle(cornerRadius: 4)
                        .fill(Color.green.opacity(0.85))
                        .frame(width: geo.size.width * buyRatio)
                }
            }
            .frame(height: 8)
        }
    }
}
