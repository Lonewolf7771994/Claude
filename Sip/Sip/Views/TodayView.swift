import SwiftUI

struct TodayView: View {
    @Environment(HydrationStore.self) private var store
    @State private var showCustom = false
    @State private var customAmount = "250"
    @State private var lastAdded: Int?
    @State private var showUndo = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    ringCard
                    weekSection
                    statsSection
                    remindersSection
                }
                .padding(.horizontal, 16)
                .padding(.bottom, 32)
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle(greeting)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Circle()
                        .fill(LinearGradient(colors: [.cyan, .blue],
                                             startPoint: .topLeading,
                                             endPoint: .bottomTrailing))
                        .overlay(Text("AK").font(.caption.weight(.semibold)).foregroundStyle(.white))
                        .frame(width: 32, height: 32)
                }
            }
            .overlay(alignment: .bottom) { undoToast }
            .alert("Custom amount", isPresented: $showCustom) {
                TextField("ml", text: $customAmount).keyboardType(.numberPad)
                Button("Cancel", role: .cancel) {}
                Button("Log") {
                    if let amt = Int(customAmount), amt > 0 { add(amt) }
                }
            }
        }
    }

    private var greeting: String {
        let h = Calendar.current.component(.hour, from: .now)
        switch h {
        case 0..<5:  return "Good night"
        case 5..<12: return "Good morning"
        case 12..<18: return "Good afternoon"
        default:     return "Good evening"
        }
    }

    private var ringCard: some View {
        VStack(spacing: 18) {
            ProgressRing(progress: store.todayProgress) {
                VStack(spacing: 2) {
                    HStack(alignment: .firstTextBaseline, spacing: 4) {
                        Text("\(store.todayTotalML)")
                            .font(.system(size: 44, weight: .bold, design: .rounded))
                            .contentTransition(.numericText())
                        Text("/ \(store.dailyGoalML) ml")
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(.secondary)
                    }
                    Text("Daily goal · stay hydrated")
                        .font(.caption)
                        .foregroundStyle(.tertiary)
                    Text("\(Int(store.todayProgress * 100))%")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(store.todayProgress >= 1 ? .green : .blue)
                        .padding(.top, 4)
                }
            }
            .frame(height: 240)
            .animation(.spring(response: 0.55, dampingFraction: 0.8), value: store.todayProgress)

            QuickAddRow { amount in
                if amount == 0 { showCustom = true } else { add(amount) }
            }
        }
        .padding(18)
        .background(Color(.secondarySystemGroupedBackground), in: .rect(cornerRadius: 24))
    }

    private var weekSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            sectionHeader("This week", trailing: "See all")
            WeekChart(days: store.last7Days, goal: store.dailyGoalML)
                .frame(height: 160)
                .padding(14)
                .background(Color(.secondarySystemGroupedBackground), in: .rect(cornerRadius: 18))
        }
    }

    private var statsSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            sectionHeader("Today")
            HStack(spacing: 10) {
                StatCard(title: "Streak",
                         value: "\(store.streakDays) day\(store.streakDays == 1 ? "" : "s")",
                         subtitle: store.streakDays > 0 ? "Keep it going" : "Hit your goal today",
                         systemImage: "flame.fill",
                         tint: .orange)
                StatCard(title: "Avg / day",
                         value: "\(store.weeklyAverageML) ml",
                         subtitle: "Last 7 days",
                         systemImage: "checkmark.circle.fill",
                         tint: .green)
            }
        }
    }

    private var remindersSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            sectionHeader("Reminders", trailing: "Edit")
            RemindersList()
        }
    }

    private func sectionHeader(_ title: String, trailing: String? = nil) -> some View {
        HStack(alignment: .firstTextBaseline) {
            Text(title).font(.title3.weight(.bold))
            Spacer()
            if let trailing {
                Button(trailing) {}.font(.subheadline).foregroundStyle(.blue)
            }
        }
        .padding(.horizontal, 4)
        .padding(.top, 8)
    }

    private var undoToast: some View {
        Group {
            if showUndo, let amount = lastAdded {
                HStack(spacing: 12) {
                    Text("+\(amount) ml logged").foregroundStyle(.white)
                    Button("Undo") {
                        store.removeLast()
                        withAnimation { showUndo = false }
                    }
                    .foregroundStyle(.cyan)
                    .fontWeight(.semibold)
                }
                .padding(.horizontal, 18)
                .padding(.vertical, 12)
                .background(Color.black.opacity(0.85), in: .capsule)
                .padding(.bottom, 16)
                .transition(.move(edge: .bottom).combined(with: .opacity))
            }
        }
    }

    private func add(_ amount: Int) {
        store.add(amount)
        lastAdded = amount
        withAnimation(.spring) { showUndo = true }
        Task {
            try? await Task.sleep(for: .seconds(2.4))
            withAnimation { showUndo = false }
        }
    }
}

private struct StatCard: View {
    let title: String
    let value: String
    let subtitle: String
    let systemImage: String
    let tint: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 8) {
                Image(systemName: systemImage)
                    .font(.caption2.weight(.bold))
                    .foregroundStyle(.white)
                    .frame(width: 18, height: 18)
                    .background(tint, in: .circle)
                Text(title.uppercased())
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(.secondary)
            }
            Text(value).font(.title3.weight(.bold))
            Text(subtitle).font(.caption).foregroundStyle(.tertiary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .background(Color(.secondarySystemGroupedBackground), in: .rect(cornerRadius: 18))
    }
}

#Preview {
    TodayView().environment(HydrationStore())
}
