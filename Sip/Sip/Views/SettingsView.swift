import SwiftUI

struct SettingsView: View {
    @Environment(HydrationStore.self) private var store

    var body: some View {
        @Bindable var store = store
        NavigationStack {
            Form {
                Section("Daily goal") {
                    Stepper(value: $store.dailyGoalML, in: 500...5000, step: 100) {
                        HStack {
                            Text("Goal")
                            Spacer()
                            Text("\(store.dailyGoalML) ml").foregroundStyle(.secondary)
                        }
                    }
                }

                Section("Apple Health") {
                    Label("Sync water intake", systemImage: "heart.fill")
                        .foregroundStyle(.pink)
                    Text("Sip writes a Water sample to the Health app for every log.")
                        .font(.footnote).foregroundStyle(.secondary)
                }

                Section("Data") {
                    Button(role: .destructive) {
                        store.clearToday()
                    } label: {
                        Label("Clear today's entries", systemImage: "trash")
                    }
                }

                Section {
                    Link("Privacy policy", destination: URL(string: "https://example.com/privacy")!)
                    Link("Support", destination: URL(string: "https://example.com/support")!)
                } footer: {
                    Text("Sip · v1.0\nMade with care.")
                        .frame(maxWidth: .infinity, alignment: .center)
                }
            }
            .navigationTitle("Settings")
        }
    }
}
