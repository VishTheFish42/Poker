#pragma once

#include <cstdint>
#include <functional>
#include <ostream>
#include <string>

namespace poker {

/// One of the four card suits.
enum class Suit : uint8_t {
    Hearts,
    Diamonds,
    Clubs,
    Spades,
};

/// One of the thirteen card ranks. The underlying value is the rank's
/// numeric strength (Two == 2 ... Ace == 14), so ranks compare directly
/// with `<` instead of needing a side lookup table.
enum class Rank : uint8_t {
    Two = 2,
    Three = 3,
    Four = 4,
    Five = 5,
    Six = 6,
    Seven = 7,
    Eight = 8,
    Nine = 9,
    Ten = 10,
    Jack = 11,
    Queen = 12,
    King = 13,
    Ace = 14,
};

/// Single-character/glyph suit symbol, e.g. "♠".
std::string suitSymbol(Suit suit);

/// Short display string for a rank, e.g. "10", "J", "A".
std::string rankDisplay(Rank rank);

/// An immutable playing card: one suit paired with one rank.
class Card {
public:
    Card(Suit suit, Rank rank) noexcept : suit_(suit), rank_(rank) {}

    Suit suit() const noexcept { return suit_; }
    Rank rank() const noexcept { return rank_; }

    /// Numeric strength of this card's rank (2-14), for hand evaluation.
    int rankValue() const noexcept { return static_cast<int>(rank_); }

    /// Compact form, e.g. "A♠".
    std::string toString() const;

    friend bool operator==(const Card& a, const Card& b) noexcept {
        return a.suit_ == b.suit_ && a.rank_ == b.rank_;
    }
    friend bool operator!=(const Card& a, const Card& b) noexcept { return !(a == b); }

    /// Cards order by rank only, matching the Python engine's `Card.__lt__`
    /// (used for sorting hole/community cards by strength).
    friend bool operator<(const Card& a, const Card& b) noexcept {
        return a.rankValue() < b.rankValue();
    }
    friend bool operator<=(const Card& a, const Card& b) noexcept { return !(b < a); }
    friend bool operator>(const Card& a, const Card& b) noexcept { return b < a; }
    friend bool operator>=(const Card& a, const Card& b) noexcept { return !(a < b); }

    friend std::ostream& operator<<(std::ostream& os, const Card& card) {
        return os << card.toString();
    }

private:
    Suit suit_;
    Rank rank_;
};

}  // namespace poker

template <>
struct std::hash<poker::Card> {
    size_t operator()(const poker::Card& card) const noexcept {
        return std::hash<int>{}(static_cast<int>(card.suit()) * 100 + card.rankValue());
    }
};
