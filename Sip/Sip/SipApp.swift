import SwiftUI

@main
struct SipApp: App {
    @State private var store = HydrationStore()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(store)
                .task {
                    await HealthKitManager.shared.requestAuthorization()
                    await ReminderScheduler.shared.requestAuthorization()
                }
        }
    }
}
