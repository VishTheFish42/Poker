#include "poker/player.hpp"

#include <gtest/gtest.h>

namespace poker {
namespace {

TEST(Player, StartsActiveWithFullStackAndNoCards) {
    Player p("Alice", 0, 1000);
    EXPECT_EQ(p.name(), "Alice");
    EXPECT_EQ(p.seat(), 0);
    EXPECT_EQ(p.stack(), 1000);
    EXPECT_TRUE(p.holeCards().empty());
    EXPECT_EQ(p.status(), PlayerStatus::Active);
    EXPECT_EQ(p.currentBet(), 0);
    EXPECT_TRUE(p.hasChips());
    EXPECT_TRUE(p.isActive());
    EXPECT_TRUE(p.canAct());
}

TEST(Player, ReceiveCardsStoresExactlyTwo) {
    Player p("Alice", 0, 1000);
    p.receiveCards(Card(Suit::Spades, Rank::Ace), Card(Suit::Hearts, Rank::King));
    ASSERT_EQ(p.holeCards().size(), 2u);
    EXPECT_EQ(p.holeCards()[0], Card(Suit::Spades, Rank::Ace));
    EXPECT_EQ(p.holeCards()[1], Card(Suit::Hearts, Rank::King));
}

TEST(Player, DiscardCardsClearsHoleCards) {
    Player p("Alice", 0, 1000);
    p.receiveCards(Card(Suit::Spades, Rank::Ace), Card(Suit::Hearts, Rank::King));
    p.discardCards();
    EXPECT_TRUE(p.holeCards().empty());
}

TEST(Player, AddChipsIncreasesStack) {
    Player p("Alice", 0, 1000);
    p.addChips(500);
    EXPECT_EQ(p.stack(), 1500);
}

TEST(Player, AddNegativeChipsThrows) {
    Player p("Alice", 0, 1000);
    EXPECT_THROW(p.addChips(-1), std::invalid_argument);
}

TEST(Player, RemoveChipsReducesStackAndTracksBet) {
    Player p("Alice", 0, 1000);
    int removed = p.removeChips(300);
    EXPECT_EQ(removed, 300);
    EXPECT_EQ(p.stack(), 700);
    EXPECT_EQ(p.currentBet(), 300);

    int removedAgain = p.removeChips(200);
    EXPECT_EQ(removedAgain, 200);
    EXPECT_EQ(p.stack(), 500);
    EXPECT_EQ(p.currentBet(), 500);
}

TEST(Player, RemoveChipsClampsToStack) {
    Player p("Alice", 0, 100);
    int removed = p.removeChips(500);
    EXPECT_EQ(removed, 100);
    EXPECT_EQ(p.stack(), 0);
    EXPECT_EQ(p.currentBet(), 100);
}

TEST(Player, RemoveNegativeChipsThrows) {
    Player p("Alice", 0, 1000);
    EXPECT_THROW(p.removeChips(-1), std::invalid_argument);
}

TEST(Player, FoldSetsFoldedStatus) {
    Player p("Alice", 0, 1000);
    p.fold();
    EXPECT_EQ(p.status(), PlayerStatus::Folded);
    EXPECT_FALSE(p.isActive());
    EXPECT_FALSE(p.canAct());
}

TEST(Player, GoAllInSetsAllInStatus) {
    Player p("Alice", 0, 1000);
    p.goAllIn();
    EXPECT_EQ(p.status(), PlayerStatus::AllIn);
    EXPECT_TRUE(p.isActive());
    EXPECT_FALSE(p.canAct());
}

TEST(Player, ResetForNewHandRestoresActiveWhenPlayerHasChips) {
    Player p("Alice", 0, 1000);
    p.receiveCards(Card(Suit::Spades, Rank::Ace), Card(Suit::Hearts, Rank::King));
    p.removeChips(200);
    p.fold();

    p.resetForNewHand();

    EXPECT_TRUE(p.holeCards().empty());
    EXPECT_EQ(p.currentBet(), 0);
    EXPECT_EQ(p.status(), PlayerStatus::Active);
}

TEST(Player, ResetForNewHandSitsOutABustedPlayer) {
    Player p("Alice", 0, 100);
    p.removeChips(100);
    ASSERT_EQ(p.stack(), 0);

    p.resetForNewHand();

    EXPECT_EQ(p.status(), PlayerStatus::SittingOut);
    EXPECT_FALSE(p.hasChips());
}

TEST(Player, SetCurrentBetRejectsNegative) {
    Player p("Alice", 0, 1000);
    EXPECT_THROW(p.setCurrentBet(-1), std::invalid_argument);
    p.setCurrentBet(50);
    EXPECT_EQ(p.currentBet(), 50);
}

}  // namespace
}  // namespace poker
