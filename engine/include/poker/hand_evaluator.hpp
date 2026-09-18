#pragma once

#include <cstdint>
#include <vector>

#include "poker/card.hpp"

namespace poker {

/// Poker hand categories, ordered from weakest to strongest by their
/// underlying value so hand types compare directly with `<`.
enum class HandType : uint8_t {
    HighCard = 1,
    OnePair = 2,
    TwoPair = 3,
    ThreeOfAKind = 4,
    Straight = 5,
    Flush = 6,
    FullHouse = 7,
    FourOfAKind = 8,
    StraightFlush = 9,
    RoyalFlush = 10,
};

/// An evaluated 5-card poker hand: its category plus enough tie-breaking
/// info (a primary rank value, then kickers in descending order) to compare
/// two hands of the same category.
class Hand {
public:
    Hand(HandType type, int rankValue, std::vector<int> kickers, std::vector<Card> cards)
        : type_(type), rankValue_(rankValue), kickers_(std::move(kickers)), cards_(std::move(cards)) {}

    HandType type() const noexcept { return type_; }
    int rankValue() const noexcept { return rankValue_; }
    const std::vector<int>& kickers() const noexcept { return kickers_; }
    const std::vector<Card>& cards() const noexcept { return cards_; }

    friend bool operator==(const Hand& a, const Hand& b) {
        return a.type_ == b.type_ && a.rankValue_ == b.rankValue_ && a.kickers_ == b.kickers_;
    }
    friend bool operator!=(const Hand& a, const Hand& b) { return !(a == b); }

    /// Ranks by category first, then primary rank value, then kickers in
    /// order (shared-prefix-only, matching Python's `zip()` semantics).
    friend bool operator<(const Hand& a, const Hand& b) {
        if (a.type_ != b.type_) {
            return static_cast<int>(a.type_) < static_cast<int>(b.type_);
        }
        if (a.rankValue_ != b.rankValue_) {
            return a.rankValue_ < b.rankValue_;
        }
        size_t n = std::min(a.kickers_.size(), b.kickers_.size());
        for (size_t i = 0; i < n; ++i) {
            if (a.kickers_[i] != b.kickers_[i]) {
                return a.kickers_[i] < b.kickers_[i];
            }
        }
        return false;
    }
    friend bool operator<=(const Hand& a, const Hand& b) { return a < b || a == b; }
    friend bool operator>(const Hand& a, const Hand& b) { return b < a; }
    friend bool operator>=(const Hand& a, const Hand& b) { return b <= a; }

private:
    HandType type_;
    int rankValue_;
    std::vector<int> kickers_;
    std::vector<Card> cards_;
};

/// Evaluates and ranks Texas Hold'em poker hands.
class HandEvaluator {
public:
    /// Evaluates exactly 5 cards. Throws std::invalid_argument otherwise.
    static Hand evaluateHand(const std::vector<Card>& cards);

    /// Finds the best 5-card hand out of exactly 7 cards (2 hole + 5
    /// community), by brute-forcing all 21 five-card combinations.
    /// Throws std::invalid_argument if not given exactly 7 cards.
    static Hand bestHandFromSeven(const std::vector<Card>& cards);
};

}  // namespace poker
