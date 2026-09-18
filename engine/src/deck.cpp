#include "poker/deck.hpp"

#include <algorithm>
#include <array>

namespace poker {

namespace {
constexpr std::array<Suit, 4> kSuits = {Suit::Hearts, Suit::Diamonds, Suit::Clubs, Suit::Spades};
constexpr std::array<Rank, 13> kRanks = {
    Rank::Two,  Rank::Three, Rank::Four, Rank::Five, Rank::Six,  Rank::Seven, Rank::Eight,
    Rank::Nine, Rank::Ten,   Rank::Jack, Rank::Queen, Rank::King, Rank::Ace,
};
}  // namespace

Deck::Deck() : rng_(std::random_device{}()) {
    reset();
}

void Deck::reset() {
    cards_.clear();
    cards_.reserve(kFullDeckSize);
    for (Suit suit : kSuits) {
        for (Rank rank : kRanks) {
            cards_.emplace_back(suit, rank);
        }
    }
}

void Deck::shuffle() {
    std::shuffle(cards_.begin(), cards_.end(), rng_);
}

void Deck::seed(unsigned int value) {
    rng_.seed(value);
}

Card Deck::dealCard() {
    if (cards_.empty()) {
        throw std::out_of_range("Cannot deal from an empty deck.");
    }
    Card top = cards_.back();
    cards_.pop_back();
    return top;
}

const Card& Deck::peekCard() const {
    if (cards_.empty()) {
        throw std::out_of_range("Cannot peek at an empty deck.");
    }
    return cards_.back();
}

}  // namespace poker
