import Foundation
import UserNotifications

enum NotificationService {

    static func send(_ signal: TradingSignal) {
        let center = UNUserNotificationCenter.current()
        let content = UNMutableNotificationContent()
        content.title = "\(signal.side.rawValue) \(signal.symbol.rawValue) \(signal.strength.emoji)"
        content.body = String(format: "@ %.2f — %@", signal.price, signal.reason)
        content.sound = .default
        content.userInfo = [
            "symbol": signal.symbol.rawValue,
            "side": signal.side.rawValue,
            "price": signal.price
        ]
        let request = UNNotificationRequest(identifier: signal.id.uuidString,
                                            content: content,
                                            trigger: nil)
        center.add(request, withCompletionHandler: nil)
    }
}
