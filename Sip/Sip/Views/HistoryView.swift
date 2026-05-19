import SwiftUI

struct HistoryView: View {
    @Environment(HydrationStore.self) private var store

    var body: some View {
        NavigationStack {
            List {
                ForEach(grouped, id: \.key) { section in
                    Section(section.key.formatted(date: .complete, time: .omitted)) {
                        ForEach(section.value) { entry in
                            HStack {
                                Image(systemName: "drop.fill").foregroundStyle(.blue)
                                Text("\(entry.amountML) ml")
                                Spacer()
                                Text(entry.date, style: .time).foregroundStyle(.secondary)
                            }
                        }
                    }
                }
            }
            .navigationTitle("History")
            .overlay {
                if store.entries.isEmpty {
                    ContentUnavailableView("No entries yet",
                                           systemImage: "drop",
                                           description: Text("Log your first sip to see it here."))
                }
            }
        }
    }

    private var grouped: [(key: Date, value: [DrinkEntry])] {
        let cal = Calendar.current
        let byDay = Dictionary(grouping: store.entries) { cal.startOfDay(for: $0.date) }
        return byDay.sorted { $0.key > $1.key }
            .map { ($0.key, $0.value.sorted { $0.date > $1.date }) }
    }
}
