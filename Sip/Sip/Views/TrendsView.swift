import SwiftUI
import Charts

struct TrendsView: View {
    @Environment(HydrationStore.self) private var store

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    Chart(store.last7Days, id: \.date) { day in
                        BarMark(
                            x: .value("Day", day.date, unit: .day),
                            y: .value("ml", day.total)
                        )
                        .foregroundStyle(
                            LinearGradient(colors: [.blue, .cyan],
                                           startPoint: .top, endPoint: .bottom)
                        )
                        .cornerRadius(6)
                    }
                    .frame(height: 240)
                    .padding(16)
                    .background(Color(.secondarySystemGroupedBackground), in: .rect(cornerRadius: 18))

                    HStack {
                        Label("Average", systemImage: "drop.fill")
                        Spacer()
                        Text("\(store.weeklyAverageML) ml")
                            .foregroundStyle(.secondary)
                    }
                    .padding()
                    .background(Color(.secondarySystemGroupedBackground), in: .rect(cornerRadius: 18))

                    HStack {
                        Label("Best day", systemImage: "trophy.fill")
                        Spacer()
                        Text("\(store.last7Days.map(\.total).max() ?? 0) ml")
                            .foregroundStyle(.secondary)
                    }
                    .padding()
                    .background(Color(.secondarySystemGroupedBackground), in: .rect(cornerRadius: 18))
                }
                .padding(16)
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("Trends")
        }
    }
}
