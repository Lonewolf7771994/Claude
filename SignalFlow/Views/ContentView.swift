import SwiftUI

struct ContentView: View {
    var body: some View {
        TabView {
            DashboardView()
                .tabItem { Label("Flow", systemImage: "waveform.path.ecg") }

            SignalsListView()
                .tabItem { Label("Signals", systemImage: "bell.badge.fill") }

            SettingsView()
                .tabItem { Label("Settings", systemImage: "gearshape") }
        }
        .tint(.orange)
    }
}

#Preview {
    ContentView()
        .environmentObject(MarketViewModel())
        .environmentObject(SignalsViewModel())
}
