import SwiftUI
import Charts

struct WeekChart: View {
    let days: [(date: Date, total: Int)]
    let goal: Int

    var body: some View {
        Chart {
            ForEach(days, id: \.date) { day in
                BarMark(
                    x: .value("Day", day.date, unit: .day),
                    y: .value("ml", day.total)
                )
                .foregroundStyle(color(for: day))
                .cornerRadius(6)
            }
            RuleMark(y: .value("Goal", goal))
                .foregroundStyle(.secondary.opacity(0.4))
                .lineStyle(StrokeStyle(lineWidth: 1, dash: [4, 4]))
        }
        .chartYAxis(.hidden)
        .chartXAxis {
            AxisMarks(values: .stride(by: .day)) { value in
                AxisValueLabel(format: .dateTime.weekday(.narrow))
            }
        }
    }

    private func color(for day: (date: Date, total: Int)) -> LinearGradient {
        let isToday = Calendar.current.isDateInToday(day.date)
        if isToday {
            return LinearGradient(colors: [.yellow, .orange],
                                  startPoint: .top, endPoint: .bottom)
        }
        if day.total < goal && day.total > 0 {
            return LinearGradient(colors: [Color(.systemGray3), Color(.systemGray4)],
                                  startPoint: .top, endPoint: .bottom)
        }
        return LinearGradient(colors: [.blue, .cyan],
                              startPoint: .top, endPoint: .bottom)
    }
}
