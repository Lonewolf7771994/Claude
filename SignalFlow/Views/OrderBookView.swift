import SwiftUI

struct OrderBookView: View {
    let book: OrderBookSnapshot

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("Order book")
                    .font(.headline)
                Spacer()
                if let spread = book.spreadBps {
                    Text(String(format: "spread %.2f bps", spread))
                        .font(.caption.monospacedDigit())
                        .foregroundStyle(.secondary)
                }
            }

            HStack(alignment: .top, spacing: 12) {
                column(levels: book.bids.prefix(10).map { $0 }, tint: .green, max: maxSize)
                column(levels: book.asks.prefix(10).map { $0 }, tint: .red, max: maxSize)
            }
        }
        .padding()
        .background(RoundedRectangle(cornerRadius: 16).fill(Color(.secondarySystemGroupedBackground)))
    }

    private var maxSize: Double {
        let all = book.bids.prefix(10).map(\.size) + book.asks.prefix(10).map(\.size)
        return all.max() ?? 1
    }

    private func column(levels: [BookLevel], tint: Color, max: Double) -> some View {
        VStack(spacing: 2) {
            ForEach(levels) { level in
                ZStack(alignment: .leading) {
                    GeometryReader { geo in
                        RoundedRectangle(cornerRadius: 2)
                            .fill(tint.opacity(0.18))
                            .frame(width: geo.size.width * CGFloat(level.size / max))
                    }
                    HStack {
                        Text(String(format: "%.2f", level.price))
                            .font(.caption2.monospacedDigit())
                        Spacer()
                        Text(String(format: "%.3f", level.size))
                            .font(.caption2.monospacedDigit())
                            .foregroundStyle(.secondary)
                    }
                    .padding(.horizontal, 6)
                }
                .frame(height: 18)
            }
        }
        .frame(maxWidth: .infinity)
    }
}
