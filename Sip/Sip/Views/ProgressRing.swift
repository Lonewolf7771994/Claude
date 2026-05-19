import SwiftUI

struct ProgressRing<Content: View>: View {
    let progress: Double
    @ViewBuilder var content: () -> Content

    var body: some View {
        ZStack {
            Circle()
                .stroke(Color(.systemFill), lineWidth: 18)
            Circle()
                .trim(from: 0, to: max(0.0001, min(1, progress)))
                .stroke(
                    LinearGradient(colors: [.cyan, .blue],
                                   startPoint: .topLeading, endPoint: .bottomTrailing),
                    style: StrokeStyle(lineWidth: 18, lineCap: .round)
                )
                .rotationEffect(.degrees(-90))
                .shadow(color: .blue.opacity(0.25), radius: 8, x: 0, y: 4)
            content()
        }
        .padding(10)
    }
}

#Preview {
    ProgressRing(progress: 0.6) {
        Text("60%").font(.largeTitle.weight(.bold))
    }
    .frame(width: 240, height: 240)
}
