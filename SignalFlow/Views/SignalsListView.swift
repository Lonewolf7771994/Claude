import SwiftUI

struct SignalsListView: View {
    @EnvironmentObject var signals: SignalsViewModel

    var body: some View {
        NavigationStack {
            Group {
                if signals.signals.isEmpty {
                    emptyState
                } else {
                    List(signals.signals) { signal in
                        SignalRow(signal: signal)
                    }
                    .listStyle(.plain)
                }
            }
            .navigationTitle("Signals")
            .toolbar {
                if !signals.signals.isEmpty {
                    ToolbarItem(placement: .topBarTrailing) {
                        Button("Clear", role: .destructive) { signals.clear() }
                    }
                }
            }
        }
    }

    private var emptyState: some View {
        VStack(spacing: 12) {
            Image(systemName: "bell.slash")
                .font(.system(size: 40))
                .foregroundStyle(.secondary)
            Text("No signals yet")
                .font(.headline)
            Text("Signals fire when order-flow delta, book imbalance and momentum align.")
                .font(.subheadline)
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)
                .padding(.horizontal, 32)
        }
    }
}

private struct SignalRow: View {
    let signal: TradingSignal

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(signal.side.rawValue)
                    .font(.caption.bold())
                    .padding(.horizontal, 8)
                    .padding(.vertical, 2)
                    .background(Capsule().fill(sideColor.opacity(0.18)))
                    .foregroundStyle(sideColor)
                Text(signal.symbol.rawValue)
                    .font(.subheadline.bold())
                Text(signal.strength.emoji)
                    .foregroundStyle(sideColor)
                Spacer()
                Text(String(format: "$%,.2f", signal.price))
                    .font(.subheadline.monospacedDigit().bold())
            }
            Text(signal.reason)
                .font(.caption)
                .foregroundStyle(.secondary)
            HStack(spacing: 10) {
                statLabel("CVD", signed(signal.cvd))
                statLabel("Imb", String(format: "%+.1f%%", signal.imbalance * 100))
                statLabel("Mom", String(format: "%+.1f bps", signal.momentum))
                Spacer()
                Text(timeString(signal.timestamp))
                    .font(.caption2.monospacedDigit())
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 4)
    }

    private var sideColor: Color { signal.side == .buy ? .green : .red }

    private func statLabel(_ k: String, _ v: String) -> some View {
        HStack(spacing: 4) {
            Text(k).font(.caption2).foregroundStyle(.secondary)
            Text(v).font(.caption2.monospacedDigit())
        }
    }

    private func signed(_ v: Double) -> String {
        let av = Swift.abs(v)
        let s: String
        switch av {
        case 1_000_000...: s = String(format: "%.2fM", av / 1_000_000)
        case 1_000...: s = String(format: "%.1fK", av / 1_000)
        default: s = String(format: "%.0f", av)
        }
        return (v >= 0 ? "+" : "−") + "$" + s
    }

    private func timeString(_ d: Date) -> String {
        let f = DateFormatter()
        f.dateFormat = "HH:mm:ss"
        return f.string(from: d)
    }
}
