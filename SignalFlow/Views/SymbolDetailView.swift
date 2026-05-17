import SwiftUI

struct SymbolDetailView: View {
    let symbol: Symbol
    @EnvironmentObject var market: MarketViewModel

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                metricsGrid
                if symbol == .btcusd, let book = market.btcBook {
                    OrderBookView(book: book)
                }
                tradesSection
            }
            .padding()
        }
        .background(Color(.systemGroupedBackground))
        .navigationTitle(symbol.rawValue)
        .navigationBarTitleDisplayMode(.inline)
    }

    private var metricsGrid: some View {
        let m = market.metrics(for: symbol)
        return LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
            tile("Last", price(m.lastPrice))
            tile("CVD (5m)", signed(m.cvd5m))
            tile("Buy vol 1m", money(m.buyVolume1m), tint: .green)
            tile("Sell vol 1m", money(m.sellVolume1m), tint: .red)
            tile("Aggressor", percent(m.aggressorRatio))
            tile("Spread bps", String(format: "%.2f", m.spreadBps))
            tile("Momentum (bps)", String(format: "%+.2f", m.momentum1m))
            tile("Large prints", "\(m.largePrintCount)")
        }
    }

    private var tradesSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Recent prints")
                .font(.headline)
            ForEach(market.recentTrades(for: symbol).prefix(40)) { trade in
                HStack {
                    Circle()
                        .fill(trade.aggressorIsBuy ? Color.green : Color.red)
                        .frame(width: 6, height: 6)
                    Text(String(format: "%.2f", trade.price))
                        .font(.subheadline.monospacedDigit())
                    Spacer()
                    Text(String(format: "%.4f", trade.quantity))
                        .font(.caption.monospacedDigit())
                        .foregroundStyle(.secondary)
                    Text(timeString(trade.timestamp))
                        .font(.caption2.monospacedDigit())
                        .foregroundStyle(.secondary)
                        .frame(width: 64, alignment: .trailing)
                }
                .padding(.vertical, 4)
                Divider()
            }
        }
        .padding()
        .background(RoundedRectangle(cornerRadius: 16).fill(Color(.secondarySystemGroupedBackground)))
    }

    private func tile(_ title: String, _ value: String, tint: Color = .primary) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(.caption2)
                .foregroundStyle(.secondary)
            Text(value)
                .font(.subheadline.monospacedDigit().bold())
                .foregroundStyle(tint)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(10)
        .background(RoundedRectangle(cornerRadius: 12).fill(Color(.secondarySystemGroupedBackground)))
    }

    private func price(_ v: Double) -> String { v > 0 ? String(format: "$%,.2f", v) : "—" }
    private func signed(_ v: Double) -> String { (v >= 0 ? "+" : "−") + money(Swift.abs(v)) }
    private func percent(_ v: Double) -> String { String(format: "%.1f%%", v * 100) }

    private func money(_ v: Double) -> String {
        switch v {
        case 1_000_000...: return String(format: "$%.2fM", v / 1_000_000)
        case 1_000...: return String(format: "$%.1fK", v / 1_000)
        default: return String(format: "$%.0f", v)
        }
    }

    private func timeString(_ d: Date) -> String {
        let f = DateFormatter()
        f.dateFormat = "HH:mm:ss"
        return f.string(from: d)
    }
}
