import Foundation
import Observation

@Observable
final class HydrationStore {
    private let storageKey = "sip.entries.v1"
    private let goalKey = "sip.goal.v1"

    var entries: [DrinkEntry] = []
    var dailyGoalML: Int {
        didSet { UserDefaults.standard.set(dailyGoalML, forKey: goalKey) }
    }

    init() {
        let stored = UserDefaults.standard.integer(forKey: goalKey)
        self.dailyGoalML = stored == 0 ? 2000 : stored
        load()
    }

    // MARK: - Derived

    var todayTotalML: Int {
        let cal = Calendar.current
        return entries
            .filter { cal.isDateInToday($0.date) }
            .reduce(0) { $0 + $1.amountML }
    }

    var todayProgress: Double {
        min(1, Double(todayTotalML) / Double(dailyGoalML))
    }

    func total(on day: Date) -> Int {
        let cal = Calendar.current
        return entries
            .filter { cal.isDate($0.date, inSameDayAs: day) }
            .reduce(0) { $0 + $1.amountML }
    }

    var last7Days: [(date: Date, total: Int)] {
        let cal = Calendar.current
        let today = cal.startOfDay(for: .now)
        return (0..<7).reversed().map { offset in
            let day = cal.date(byAdding: .day, value: -offset, to: today)!
            return (day, total(on: day))
        }
    }

    var streakDays: Int {
        let cal = Calendar.current
        var streak = 0
        var day = cal.startOfDay(for: .now)
        while total(on: day) >= dailyGoalML {
            streak += 1
            day = cal.date(byAdding: .day, value: -1, to: day)!
        }
        return streak
    }

    var weeklyAverageML: Int {
        let totals = last7Days.map(\.total).filter { $0 > 0 }
        guard !totals.isEmpty else { return 0 }
        return totals.reduce(0, +) / totals.count
    }

    // MARK: - Mutations

    func add(_ amountML: Int) {
        let entry = DrinkEntry(amountML: amountML)
        entries.append(entry)
        save()
        Task { await HealthKitManager.shared.save(amountML: amountML, date: entry.date) }
    }

    @discardableResult
    func removeLast() -> DrinkEntry? {
        guard let last = entries.popLast() else { return nil }
        save()
        return last
    }

    func clearToday() {
        let cal = Calendar.current
        entries.removeAll { cal.isDateInToday($0.date) }
        save()
    }

    // MARK: - Persistence

    private func save() {
        guard let data = try? JSONEncoder().encode(entries) else { return }
        UserDefaults.standard.set(data, forKey: storageKey)
    }

    private func load() {
        guard let data = UserDefaults.standard.data(forKey: storageKey),
              let decoded = try? JSONDecoder().decode([DrinkEntry].self, from: data) else { return }
        entries = decoded
    }
}
