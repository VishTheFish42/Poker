#include "poker/hand_evaluator.hpp"

#include <gtest/gtest.h>

namespace poker {
namespace {

std::vector<Card> cards(std::initializer_list<std::pair<Suit, Rank>> spec) {
    std::vector<Card> result;
    for (auto [suit, rank] : spec) {
        result.emplace_back(suit, rank);
    }
    return result;
}

TEST(HandEvaluator, RejectsWrongCardCounts) {
    EXPECT_THROW(HandEvaluator::evaluateHand({}), std::invalid_argument);
    EXPECT_THROW(HandEvaluator::evaluateHand(cards({{Suit::Spades, Rank::Ace}})), std::invalid_argument);
}

TEST(HandEvaluator, RoyalFlush) {
    Hand h = HandEvaluator::evaluateHand(cards({
        {Suit::Spades, Rank::Ace}, {Suit::Spades, Rank::King}, {Suit::Spades, Rank::Queen},
        {Suit::Spades, Rank::Jack}, {Suit::Spades, Rank::Ten},
    }));
    EXPECT_EQ(h.type(), HandType::RoyalFlush);
    EXPECT_EQ(h.rankValue(), 14);
}

TEST(HandEvaluator, StraightFlush) {
    Hand h = HandEvaluator::evaluateHand(cards({
        {Suit::Hearts, Rank::Nine}, {Suit::Hearts, Rank::Eight}, {Suit::Hearts, Rank::Seven},
        {Suit::Hearts, Rank::Six}, {Suit::Hearts, Rank::Five},
    }));
    EXPECT_EQ(h.type(), HandType::StraightFlush);
    EXPECT_EQ(h.rankValue(), 9);
}

TEST(HandEvaluator, WheelStraightFlushPlaysAsFiveHigh) {
    Hand h = HandEvaluator::evaluateHand(cards({
        {Suit::Clubs, Rank::Ace}, {Suit::Clubs, Rank::Two}, {Suit::Clubs, Rank::Three},
        {Suit::Clubs, Rank::Four}, {Suit::Clubs, Rank::Five},
    }));
    EXPECT_EQ(h.type(), HandType::StraightFlush);
    EXPECT_EQ(h.rankValue(), 5);
}

TEST(HandEvaluator, FourOfAKind) {
    Hand h = HandEvaluator::evaluateHand(cards({
        {Suit::Spades, Rank::King}, {Suit::Hearts, Rank::King}, {Suit::Diamonds, Rank::King},
        {Suit::Clubs, Rank::King}, {Suit::Spades, Rank::Two},
    }));
    EXPECT_EQ(h.type(), HandType::FourOfAKind);
    EXPECT_EQ(h.rankValue(), 13);
    ASSERT_EQ(h.kickers().size(), 1u);
    EXPECT_EQ(h.kickers()[0], 2);
}

TEST(HandEvaluator, FullHouse) {
    Hand h = HandEvaluator::evaluateHand(cards({
        {Suit::Spades, Rank::Three}, {Suit::Hearts, Rank::Three}, {Suit::Diamonds, Rank::Three},
        {Suit::Clubs, Rank::Nine}, {Suit::Spades, Rank::Nine},
    }));
    EXPECT_EQ(h.type(), HandType::FullHouse);
    EXPECT_EQ(h.rankValue(), 3);
    ASSERT_EQ(h.kickers().size(), 1u);
    EXPECT_EQ(h.kickers()[0], 9);
}

TEST(HandEvaluator, Flush) {
    Hand h = HandEvaluator::evaluateHand(cards({
        {Suit::Diamonds, Rank::Two}, {Suit::Diamonds, Rank::Seven}, {Suit::Diamonds, Rank::Nine},
        {Suit::Diamonds, Rank::Jack}, {Suit::Diamonds, Rank::King},
    }));
    EXPECT_EQ(h.type(), HandType::Flush);
    EXPECT_EQ(h.rankValue(), 13);
    EXPECT_EQ(h.kickers(), (std::vector<int>{11, 9, 7, 2}));
}

TEST(HandEvaluator, Straight) {
    Hand h = HandEvaluator::evaluateHand(cards({
        {Suit::Spades, Rank::Six}, {Suit::Hearts, Rank::Seven}, {Suit::Diamonds, Rank::Eight},
        {Suit::Clubs, Rank::Nine}, {Suit::Spades, Rank::Ten},
    }));
    EXPECT_EQ(h.type(), HandType::Straight);
    EXPECT_EQ(h.rankValue(), 10);
}

TEST(HandEvaluator, WheelStraightPlaysAsFiveHigh) {
    Hand h = HandEvaluator::evaluateHand(cards({
        {Suit::Spades, Rank::Ace}, {Suit::Hearts, Rank::Two}, {Suit::Diamonds, Rank::Three},
        {Suit::Clubs, Rank::Four}, {Suit::Hearts, Rank::Five},
    }));
    EXPECT_EQ(h.type(), HandType::Straight);
    EXPECT_EQ(h.rankValue(), 5);
}

TEST(HandEvaluator, ThreeOfAKind) {
    Hand h = HandEvaluator::evaluateHand(cards({
        {Suit::Spades, Rank::Four}, {Suit::Hearts, Rank::Four}, {Suit::Diamonds, Rank::Four},
        {Suit::Clubs, Rank::King}, {Suit::Spades, Rank::Two},
    }));
    EXPECT_EQ(h.type(), HandType::ThreeOfAKind);
    EXPECT_EQ(h.rankValue(), 4);
    EXPECT_EQ(h.kickers(), (std::vector<int>{13, 2}));
}

TEST(HandEvaluator, TwoPair) {
    Hand h = HandEvaluator::evaluateHand(cards({
        {Suit::Spades, Rank::Jack}, {Suit::Hearts, Rank::Jack}, {Suit::Diamonds, Rank::Four},
        {Suit::Clubs, Rank::Four}, {Suit::Spades, Rank::Two},
    }));
    EXPECT_EQ(h.type(), HandType::TwoPair);
    EXPECT_EQ(h.rankValue(), 11);
    EXPECT_EQ(h.kickers(), (std::vector<int>{4, 2}));
}

TEST(HandEvaluator, OnePair) {
    Hand h = HandEvaluator::evaluateHand(cards({
        {Suit::Spades, Rank::Eight}, {Suit::Hearts, Rank::Eight}, {Suit::Diamonds, Rank::King},
        {Suit::Clubs, Rank::Four}, {Suit::Spades, Rank::Two},
    }));
    EXPECT_EQ(h.type(), HandType::OnePair);
    EXPECT_EQ(h.rankValue(), 8);
    EXPECT_EQ(h.kickers(), (std::vector<int>{13, 4, 2}));
}

TEST(HandEvaluator, HighCard) {
    Hand h = HandEvaluator::evaluateHand(cards({
        {Suit::Spades, Rank::King}, {Suit::Hearts, Rank::Jack}, {Suit::Diamonds, Rank::Eight},
        {Suit::Clubs, Rank::Four}, {Suit::Spades, Rank::Two},
    }));
    EXPECT_EQ(h.type(), HandType::HighCard);
    EXPECT_EQ(h.rankValue(), 13);
    EXPECT_EQ(h.kickers(), (std::vector<int>{11, 8, 4, 2}));
}

TEST(Hand, OrdersByTypeThenRankThenKickers) {
    Hand pair = HandEvaluator::evaluateHand(cards({
        {Suit::Spades, Rank::Eight}, {Suit::Hearts, Rank::Eight}, {Suit::Diamonds, Rank::King},
        {Suit::Clubs, Rank::Four}, {Suit::Spades, Rank::Two},
    }));
    Hand twoPair = HandEvaluator::evaluateHand(cards({
        {Suit::Spades, Rank::Jack}, {Suit::Hearts, Rank::Jack}, {Suit::Diamonds, Rank::Four},
        {Suit::Clubs, Rank::Four}, {Suit::Spades, Rank::Two},
    }));
    EXPECT_LT(pair, twoPair);
    EXPECT_GT(twoPair, pair);

    Hand higherPair = HandEvaluator::evaluateHand(cards({
        {Suit::Diamonds, Rank::Nine}, {Suit::Clubs, Rank::Nine}, {Suit::Hearts, Rank::King},
        {Suit::Spades, Rank::Four}, {Suit::Hearts, Rank::Two},
    }));
    EXPECT_LT(pair, higherPair);
}

TEST(Hand, EqualHandsCompareEqual) {
    Hand a = HandEvaluator::evaluateHand(cards({
        {Suit::Spades, Rank::King}, {Suit::Hearts, Rank::Jack}, {Suit::Diamonds, Rank::Eight},
        {Suit::Clubs, Rank::Four}, {Suit::Spades, Rank::Two},
    }));
    Hand b = HandEvaluator::evaluateHand(cards({
        {Suit::Clubs, Rank::King}, {Suit::Diamonds, Rank::Jack}, {Suit::Hearts, Rank::Eight},
        {Suit::Spades, Rank::Four}, {Suit::Hearts, Rank::Two},
    }));
    EXPECT_EQ(a, b);
    EXPECT_LE(a, b);
    EXPECT_GE(a, b);
}

TEST(HandEvaluator, BestHandFromSevenRejectsWrongCount) {
    EXPECT_THROW(HandEvaluator::bestHandFromSeven({}), std::invalid_argument);
}

TEST(HandEvaluator, BestHandFromSevenPicksBestFiveOfSeven) {
    // Hole: pocket aces. Board: A-K-Q-J-T all diamonds except the pocket
    // aces - the best 5-card hand is the broadway straight flush on the
    // board plus... actually make it unambiguous: board gives a straight
    // flush outright, which must beat the trip aces also available.
    std::vector<Card> seven = cards({
        {Suit::Spades, Rank::Ace}, {Suit::Hearts, Rank::Ace},        // hole cards
        {Suit::Diamonds, Rank::King}, {Suit::Diamonds, Rank::Queen}, {Suit::Diamonds, Rank::Jack},
        {Suit::Diamonds, Rank::Ten}, {Suit::Diamonds, Rank::Nine},   // board
    });
    Hand best = HandEvaluator::bestHandFromSeven(seven);
    EXPECT_EQ(best.type(), HandType::StraightFlush);
    EXPECT_EQ(best.rankValue(), 13);
}

TEST(HandEvaluator, BestHandFromSevenUsesBothHoleCardsWhenStrongest) {
    std::vector<Card> seven = cards({
        {Suit::Spades, Rank::Ace}, {Suit::Hearts, Rank::Ace},
        {Suit::Diamonds, Rank::Ace}, {Suit::Clubs, Rank::Ace},
        {Suit::Spades, Rank::King}, {Suit::Hearts, Rank::Queen}, {Suit::Diamonds, Rank::Two},
    });
    Hand best = HandEvaluator::bestHandFromSeven(seven);
    EXPECT_EQ(best.type(), HandType::FourOfAKind);
    EXPECT_EQ(best.rankValue(), 14);
    ASSERT_EQ(best.kickers().size(), 1u);
    EXPECT_EQ(best.kickers()[0], 13);
}

}  // namespace
}  // namespace poker
