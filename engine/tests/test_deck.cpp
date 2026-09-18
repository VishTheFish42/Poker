#include "poker/deck.hpp"

#include <gtest/gtest.h>

#include <algorithm>
#include <unordered_set>

namespace poker {
namespace {

TEST(Deck, StartsWithFiftyTwoUniqueCards) {
    Deck deck;
    EXPECT_EQ(deck.remaining(), Deck::kFullDeckSize);
    EXPECT_FALSE(deck.isEmpty());

    std::unordered_set<Card> unique(deck.begin(), deck.end());
    EXPECT_EQ(unique.size(), Deck::kFullDeckSize);
}

TEST(Deck, DealCardRemovesFromTop) {
    Deck deck;
    Card top = deck.peekCard();
    Card dealt = deck.dealCard();
    EXPECT_EQ(top, dealt);
    EXPECT_EQ(deck.remaining(), Deck::kFullDeckSize - 1);
}

TEST(Deck, DealingAllCardsEmptiesTheDeck) {
    Deck deck;
    for (size_t i = 0; i < Deck::kFullDeckSize; ++i) {
        deck.dealCard();
    }
    EXPECT_TRUE(deck.isEmpty());
    EXPECT_EQ(deck.remaining(), 0u);
}

TEST(Deck, DealCardOnEmptyDeckThrows) {
    Deck deck;
    for (size_t i = 0; i < Deck::kFullDeckSize; ++i) {
        deck.dealCard();
    }
    EXPECT_THROW(deck.dealCard(), std::out_of_range);
}

TEST(Deck, PeekCardOnEmptyDeckThrows) {
    Deck deck;
    for (size_t i = 0; i < Deck::kFullDeckSize; ++i) {
        deck.dealCard();
    }
    EXPECT_THROW(deck.peekCard(), std::out_of_range);
}

TEST(Deck, ResetRestoresFullUnshuffledDeck) {
    Deck deck;
    Card firstBeforeReset = deck.peekCard();
    deck.dealCard();
    deck.dealCard();
    deck.reset();
    EXPECT_EQ(deck.remaining(), Deck::kFullDeckSize);
    EXPECT_EQ(deck.peekCard(), firstBeforeReset);
}

TEST(Deck, ShuffleKeepsAllFiftyTwoUniqueCards) {
    Deck deck;
    deck.seed(42);
    deck.shuffle();
    EXPECT_EQ(deck.remaining(), Deck::kFullDeckSize);

    std::unordered_set<Card> unique(deck.begin(), deck.end());
    EXPECT_EQ(unique.size(), Deck::kFullDeckSize);
}

TEST(Deck, SameSeedProducesSameShuffleOrder) {
    Deck a;
    a.seed(7);
    a.shuffle();

    Deck b;
    b.seed(7);
    b.shuffle();

    EXPECT_TRUE(std::equal(a.begin(), a.end(), b.begin(), b.end()));
}

TEST(Deck, ShuffleChangesCardOrder) {
    Deck a;
    a.seed(1);
    Deck b;
    b.seed(1);
    b.shuffle();

    EXPECT_FALSE(std::equal(a.begin(), a.end(), b.begin(), b.end()));
}

}  // namespace
}  // namespace poker
