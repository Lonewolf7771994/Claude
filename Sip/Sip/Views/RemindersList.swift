import SwiftUI

struct RemindersList: View {
    @AppStorage("sip.reminder.morning") private var morning = true
    @AppStorage("sip.reminder.midday") private var midday = true
    @AppStorage("sip.reminder.evening") private var evening = false

    var body: some View {
        VStack(spacing: 0) {
            row(icon: "sunrise.fill",
                tint: LinearGradient(colors: [.cyan, .blue], startPoint: .topLeading, endPoint: .bottomTrailing),
                title: "Morning kickstart",
                meta: "Every day · 8:00",
                isOn: $morning,
                hour: 8)
            Divider().padding(.leading, 56)
            row(icon: "sun.max.fill",
                tint: LinearGradient(colors: [.yellow, .orange], startPoint: .topLeading, endPoint: .bottomTrailing),
                title: "Midday top‑up",
                meta: "Weekdays · 13:00",
                isOn: $midday,
                hour: 13)
            Divider().padding(.leading, 56)
            row(icon: "moon.fill",
                tint: LinearGradient(colors: [.indigo, .blue], startPoint: .topLeading, endPoint: .bottomTrailing),
                title: "Evening wind‑down",
                meta: "Every day · 20:30",
                isOn: $evening,
                hour: 20)
        }
        .background(Color(.secondarySystemGroupedBackground), in: .rect(cornerRadius: 18))
    }

    private func row(icon: String,
                     tint: LinearGradient,
                     title: String,
                     meta: String,
                     isOn: Binding<Bool>,
                     hour: Int) -> some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .font(.system(size: 14, weight: .semibold))
                .foregroundStyle(.white)
                .frame(width: 30, height: 30)
                .background(tint, in: .rect(cornerRadius: 8))
            VStack(alignment: .leading, spacing: 2) {
                Text(title).font(.subheadline)
                Text(meta).font(.caption).foregroundStyle(.secondary)
            }
            Spacer()
            Toggle("", isOn: isOn).labelsHidden()
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 10)
        .onChange(of: isOn.wrappedValue) { _, newValue in
            Task {
                if newValue {
                    await ReminderScheduler.shared.schedule(id: title, hour: hour, minute: 0)
                } else {
                    await ReminderScheduler.shared.cancel(id: title)
                }
            }
        }
    }
}
