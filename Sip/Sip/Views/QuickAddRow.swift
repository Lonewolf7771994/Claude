import SwiftUI

struct QuickAddRow: View {
    let onAdd: (Int) -> Void

    var body: some View {
        HStack(spacing: 10) {
            tile(amount: 200, label: "Glass", icon: "cup.and.saucer.fill")
            tile(amount: 350, label: "Bottle", icon: "waterbottle.fill")
            tile(amount: 500, label: "Large", icon: "mug.fill")
            customTile
        }
    }

    private func tile(amount: Int, label: String, icon: String) -> some View {
        Button { onAdd(amount) } label: {
            VStack(spacing: 6) {
                Image(systemName: icon)
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(.white)
                    .frame(width: 34, height: 34)
                    .background(
                        LinearGradient(colors: [.cyan, .blue],
                                       startPoint: .topLeading, endPoint: .bottomTrailing),
                        in: .circle
                    )
                Text("\(amount) ml").font(.footnote.weight(.semibold))
                Text(label).font(.caption2).foregroundStyle(.secondary)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 12)
            .background(Color(.tertiarySystemGroupedBackground), in: .rect(cornerRadius: 16))
        }
        .buttonStyle(.plain)
        .sensoryFeedback(.impact(weight: .light), trigger: amount)
    }

    private var customTile: some View {
        Button { onAdd(0) } label: {
            VStack(spacing: 6) {
                Image(systemName: "plus")
                    .font(.system(size: 16, weight: .bold))
                    .foregroundStyle(.white)
                    .frame(width: 34, height: 34)
                    .background(
                        LinearGradient(colors: [.orange, .red],
                                       startPoint: .topLeading, endPoint: .bottomTrailing),
                        in: .circle
                    )
                Text("Custom").font(.footnote.weight(.semibold))
                Text("Coffee, tea…").font(.caption2).foregroundStyle(.secondary)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 12)
            .background(Color(.tertiarySystemGroupedBackground), in: .rect(cornerRadius: 16))
        }
        .buttonStyle(.plain)
    }
}

#Preview {
    QuickAddRow { _ in }.padding()
}
