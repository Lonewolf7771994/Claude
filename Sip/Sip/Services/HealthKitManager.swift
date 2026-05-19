import Foundation
#if canImport(HealthKit)
import HealthKit
#endif

@MainActor
final class HealthKitManager {
    static let shared = HealthKitManager()

    #if canImport(HealthKit)
    private let store = HKHealthStore()
    private let waterType = HKQuantityType(.dietaryWater)
    #endif

    private(set) var isAuthorized = false

    private init() {}

    func requestAuthorization() async {
        #if canImport(HealthKit)
        guard HKHealthStore.isHealthDataAvailable() else { return }
        do {
            try await store.requestAuthorization(toShare: [waterType], read: [waterType])
            isAuthorized = true
        } catch {
            isAuthorized = false
        }
        #endif
    }

    func save(amountML: Int, date: Date) async {
        #if canImport(HealthKit)
        guard isAuthorized else { return }
        let quantity = HKQuantity(unit: .literUnit(with: .milli), doubleValue: Double(amountML))
        let sample = HKQuantitySample(type: waterType, quantity: quantity, start: date, end: date)
        try? await store.save(sample)
        #endif
    }
}
