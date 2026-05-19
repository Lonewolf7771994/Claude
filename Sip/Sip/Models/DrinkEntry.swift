import Foundation

struct DrinkEntry: Identifiable, Codable, Hashable {
    let id: UUID
    let date: Date
    let amountML: Int

    init(id: UUID = UUID(), date: Date = .now, amountML: Int) {
        self.id = id
        self.date = date
        self.amountML = amountML
    }
}
