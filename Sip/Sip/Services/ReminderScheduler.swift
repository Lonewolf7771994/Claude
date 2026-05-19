import Foundation
import UserNotifications

@MainActor
final class ReminderScheduler {
    static let shared = ReminderScheduler()
    private init() {}

    func requestAuthorization() async {
        let center = UNUserNotificationCenter.current()
        _ = try? await center.requestAuthorization(options: [.alert, .sound, .badge])
    }

    func schedule(id: String, hour: Int, minute: Int) async {
        let content = UNMutableNotificationContent()
        content.title = "Time to hydrate"
        content.body = "A quick sip keeps your streak alive."
        content.sound = .default

        var date = DateComponents()
        date.hour = hour
        date.minute = minute

        let trigger = UNCalendarNotificationTrigger(dateMatching: date, repeats: true)
        let request = UNNotificationRequest(identifier: id, content: content, trigger: trigger)
        try? await UNUserNotificationCenter.current().add(request)
    }

    func cancel(id: String) async {
        UNUserNotificationCenter.current().removePendingNotificationRequests(withIdentifiers: [id])
    }
}
