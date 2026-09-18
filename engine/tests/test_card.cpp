#include "poker/card.hpp"

#include <gtest/gtest.h>

#include <sstream>
#include <unordered_set>

namespace poker {
namespace {

TEST(Card, StoresSuitAndRank) {
    Card card(Suit::Spades, Rank::Ace);
    EXPECT_EQ(card.suit(), Suit::Spades);
    EXPECT_EQ(card.rank(), Rank::Ace);
}

TEST(Card, RankValueMatchesNumericStrength) {
    EXPECT_EQ(Card(Suit::Hearts, Rank::Two).rankValue(), 2);
    EXPECT_EQ(Card(Suit::Hearts, Rank::Ten).rankValue(), 10);
    EXPECT_EQ(Card(Suit::Hearts, Rank::Ace).rankValue(), 14);
}

TEST(Card, EqualityComparesSuitAndRank) {
    EXPECT_EQ(Card(Suit::Clubs, Rank::King), Card(Suit::Clubs, Rank::King));
    EXPECT_NE(Card(Suit::Clubs, Rank::King), Card(Suit::Diamonds, Rank::King));
    EXPECT_NE(Card(Suit::Clubs, Rank::King), Card(Suit::Clubs, Rank::Queen));
}

TEST(Card, OrdersByRankOnly) {
    Card low(Suit::Spades, Rank::Two);
    Card high(Suit::Hearts, Rank::Ace);
    EXPECT_LT(low, high);
    EXPECT_LE(low, high);
    EXPECT_GT(high, low);
    EXPECT_GE(high, low);
    EXPECT_FALSE(high < low);
}

TEST(Card, ToStringIsRankThenSuit) {
    EXPECT_EQ(Card(Suit::Spades, Rank::Ace).toString(), "A♠");
    EXPECT_EQ(Card(Suit::Hearts, Rank::Ten).toString(), "10♥");
}

TEST(Card, StreamOperatorMatchesToString) {
    std::ostringstream out;
    out << Card(Suit::Diamonds, Rank::Jack);
    EXPECT_EQ(out.str(), "J♦");
}

TEST(Card, IsHashableForUseInSets) {
    std::unordered_set<Card> seen;
    seen.insert(Card(Suit::Clubs, Rank::Five));
    seen.insert(Card(Suit::Clubs, Rank::Five));
    seen.insert(Card(Suit::Hearts, Rank::Five));
    EXPECT_EQ(seen.size(), 2u);
}

}  // namespace
}  // namespace poker
