#pragma once

#include <cstddef>
#include <random>
#include <stdexcept>
#include <vector>

#include "poker/card.hpp"

namespace poker {

/// A standard 52-card deck. Cards are dealt from the back of an internal
/// vector so `dealCard()`/`peekCard()` are O(1); `shuffle()` permutes the
/// whole vector.
class Deck {
public:
    static constexpr size_t kFullDeckSize = 52;

    /// Builds a full, unshuffled deck and seeds its own RNG from
    /// `std::random_device` so distinct decks don't share a shuffle order.
    Deck();

    /// Restores all 52 cards in canonical (unshuffled) order.
    void reset();

    /// Randomly permutes the remaining cards using this deck's RNG.
    void shuffle();

    /// Reseeds this deck's RNG, e.g. for a deterministic test shuffle.
    void seed(unsigned int value);

    /// Removes and returns the top card.
    /// Throws std::out_of_range if the deck is empty.
    Card dealCard();

    /// Returns the top card without removing it.
    /// Throws std::out_of_range if the deck is empty.
    const Card& peekCard() const;

    size_t remaining() const noexcept { return cards_.size(); }
    bool isEmpty() const noexcept { return cards_.empty(); }

    std::vector<Card>::const_iterator begin() const noexcept { return cards_.begin(); }
    std::vector<Card>::const_iterator end() const noexcept { return cards_.end(); }

private:
    std::vector<Card> cards_;
    std::mt19937 rng_;
};

}  // namespace poker
