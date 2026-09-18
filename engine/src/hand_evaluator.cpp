#include "poker/hand_evaluator.hpp"

#include <algorithm>
#include <array>
#include <map>
#include <stdexcept>

namespace poker {

namespace {

/// Rank value (2-14) -> how many of the 5 cards have that rank.
std::map<int, int, std::greater<>> countRanks(const std::vector<Card>& cards) {
    std::map<int, int, std::greater<>> counts;
    for (const Card& card : cards) {
        counts[card.rankValue()]++;
    }
    return counts;
}

bool isFlush(const std::vector<Card>& cards) {
    return std::all_of(cards.begin(), cards.end(),
                        [&](const Card& c) { return c.suit() == cards.front().suit(); });
}

/// Returns the sorted (ascending) rank values of the 5 cards.
std::array<int, 5> sortedRanks(const std::vector<Card>& cards) {
    std::array<int, 5> ranks{};
    for (size_t i = 0; i < 5; ++i) {
        ranks[i] = cards[i].rankValue();
    }
    std::sort(ranks.begin(), ranks.end());
    return ranks;
}

/// Rank values of the 5 cards, sorted descending.
std::array<int, 5> sortedRanksDescending(const std::vector<Card>& cards) {
    std::array<int, 5> ranks = sortedRanks(cards);
    std::reverse(ranks.begin(), ranks.end());
    return ranks;
}

bool isStraight(const std::vector<Card>& cards) {
    std::array<int, 5> ranks = sortedRanks(cards);
    bool allUnique = std::adjacent_find(ranks.begin(), ranks.end()) == ranks.end();
    if (allUnique && ranks[4] - ranks[0] == 4) {
        return true;
    }
    // Wheel: A-2-3-4-5.
    return ranks == std::array<int, 5>{2, 3, 4, 5, 14};
}

/// High card of a straight; the wheel (A-2-3-4-5) plays as a 5-high.
int straightHigh(const std::vector<Card>& cards) {
    std::array<int, 5> ranks = sortedRanks(cards);
    if (ranks == std::array<int, 5>{2, 3, 4, 5, 14}) {
        return 5;
    }
    return ranks[4];
}

/// Ranks with a given multiplicity, most-common-count first then
/// descending rank value (matches the Python implementation's use of
/// `sorted(..., reverse=True)` over a `set`).
std::vector<int> ranksWithCount(const std::map<int, int, std::greater<>>& counts, int count) {
    std::vector<int> result;
    for (const auto& [rank, n] : counts) {
        if (n == count) {
            result.push_back(rank);
        }
    }
    return result;
}

Hand evaluateStraightFlush(const std::vector<Card>& cards) {
    int high = straightHigh(cards);
    if (high == 14) {
        return Hand(HandType::RoyalFlush, 14, {}, cards);
    }
    return Hand(HandType::StraightFlush, high, {}, cards);
}

Hand evaluateFourOfAKind(const std::vector<Card>& cards, const std::map<int, int, std::greater<>>& counts) {
    int quad = ranksWithCount(counts, 4).front();
    int kicker = ranksWithCount(counts, 1).front();
    return Hand(HandType::FourOfAKind, quad, {kicker}, cards);
}

Hand evaluateFullHouse(const std::vector<Card>& cards, const std::map<int, int, std::greater<>>& counts) {
    int trips = ranksWithCount(counts, 3).front();
    int pair = ranksWithCount(counts, 2).front();
    return Hand(HandType::FullHouse, trips, {pair}, cards);
}

Hand evaluateFlush(const std::vector<Card>& cards) {
    std::array<int, 5> ranks = sortedRanksDescending(cards);
    return Hand(HandType::Flush, ranks[0], {ranks.begin() + 1, ranks.end()}, cards);
}

Hand evaluateStraight(const std::vector<Card>& cards) {
    return Hand(HandType::Straight, straightHigh(cards), {}, cards);
}

Hand evaluateThreeOfAKind(const std::vector<Card>& cards, const std::map<int, int, std::greater<>>& counts) {
    int trips = ranksWithCount(counts, 3).front();
    std::vector<int> kickers = ranksWithCount(counts, 1);
    return Hand(HandType::ThreeOfAKind, trips, kickers, cards);
}

Hand evaluateTwoPair(const std::vector<Card>& cards, const std::map<int, int, std::greater<>>& counts) {
    std::vector<int> pairs = ranksWithCount(counts, 2);
    int kicker = ranksWithCount(counts, 1).front();
    return Hand(HandType::TwoPair, pairs[0], {pairs[1], kicker}, cards);
}

Hand evaluateOnePair(const std::vector<Card>& cards, const std::map<int, int, std::greater<>>& counts) {
    int pair = ranksWithCount(counts, 2).front();
    std::vector<int> kickers = ranksWithCount(counts, 1);
    return Hand(HandType::OnePair, pair, kickers, cards);
}

Hand evaluateHighCard(const std::vector<Card>& cards) {
    std::array<int, 5> ranks = sortedRanksDescending(cards);
    return Hand(HandType::HighCard, ranks[0], {ranks.begin() + 1, ranks.end()}, cards);
}

}  // namespace

Hand HandEvaluator::evaluateHand(const std::vector<Card>& cards) {
    if (cards.size() != 5) {
        throw std::invalid_argument("Must evaluate exactly 5 cards.");
    }

    bool flush = isFlush(cards);
    bool straight = isStraight(cards);
    if (flush && straight) {
        return evaluateStraightFlush(cards);
    }

    std::map<int, int, std::greater<>> counts = countRanks(cards);
    int maxCount = 0;
    for (const auto& [rank, n] : counts) {
        maxCount = std::max(maxCount, n);
    }

    if (maxCount == 4) {
        return evaluateFourOfAKind(cards, counts);
    }
    if (counts.size() == 2 && maxCount == 3) {
        return evaluateFullHouse(cards, counts);
    }
    if (flush) {
        return evaluateFlush(cards);
    }
    if (straight) {
        return evaluateStraight(cards);
    }
    if (maxCount == 3) {
        return evaluateThreeOfAKind(cards, counts);
    }
    if (counts.size() == 3 && maxCount == 2) {
        return evaluateTwoPair(cards, counts);
    }
    if (maxCount == 2) {
        return evaluateOnePair(cards, counts);
    }
    return evaluateHighCard(cards);
}

Hand HandEvaluator::bestHandFromSeven(const std::vector<Card>& cards) {
    if (cards.size() != 7) {
        throw std::invalid_argument("Must provide exactly 7 cards for best hand selection.");
    }

    // All 21 ways to omit 2 of the 7 cards.
    std::vector<Hand> best;
    for (size_t skipA = 0; skipA < 7; ++skipA) {
        for (size_t skipB = skipA + 1; skipB < 7; ++skipB) {
            std::vector<Card> five;
            five.reserve(5);
            for (size_t i = 0; i < 7; ++i) {
                if (i != skipA && i != skipB) {
                    five.push_back(cards[i]);
                }
            }
            Hand hand = evaluateHand(five);
            if (best.empty() || hand > best.front()) {
                best.clear();
                best.push_back(std::move(hand));
            }
        }
    }
    return best.front();
}

}  // namespace poker
