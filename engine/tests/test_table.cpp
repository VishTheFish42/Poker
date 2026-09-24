#include "poker/table.hpp"

#include <gtest/gtest.h>

namespace poker {
namespace {

TEST(Table, RejectsInvalidSeatCounts) {
    EXPECT_THROW(Table(1), std::invalid_argument);
    EXPECT_THROW(Table(11), std::invalid_argument);
    EXPECT_NO_THROW(Table(2));
    EXPECT_NO_THROW(Table(10));
}

TEST(Table, StreetNumberMapping) {
    EXPECT_EQ(streetNumber(Street::PreFlop), 0);
    EXPECT_EQ(streetNumber(Street::Flop), 1);
    EXPECT_EQ(streetNumber(Street::Turn), 2);
    EXPECT_EQ(streetNumber(Street::River), 3);
    EXPECT_EQ(streetNumber(Street::Showdown), 4);
    EXPECT_EQ(streetNumber(Street::HandComplete), -1);
}

TEST(Table, AddAndGetPlayer) {
    Table table(6);
    table.addPlayer(Player("Alice", 0, 1000));
    Player* p = table.getPlayer(0);
    ASSERT_NE(p, nullptr);
    EXPECT_EQ(p->name(), "Alice");
    EXPECT_EQ(table.getPlayer(1), nullptr);
}

TEST(Table, AddPlayerRejectsInvalidOrOccupiedSeat) {
    Table table(6);
    EXPECT_THROW(table.addPlayer(Player("Bad", 6, 1000)), std::invalid_argument);
    EXPECT_THROW(table.addPlayer(Player("Bad", -1, 1000)), std::invalid_argument);
    table.addPlayer(Player("Alice", 0, 1000));
    EXPECT_THROW(table.addPlayer(Player("Bob", 0, 1000)), std::invalid_argument);
}

TEST(Table, RemovePlayerReturnsAndEmptiesSeat) {
    Table table(6);
    table.addPlayer(Player("Alice", 0, 1000));
    std::optional<Player> removed = table.removePlayer(0);
    ASSERT_TRUE(removed.has_value());
    EXPECT_EQ(removed->name(), "Alice");
    EXPECT_EQ(table.getPlayer(0), nullptr);
    EXPECT_FALSE(table.removePlayer(0).has_value());
    EXPECT_FALSE(table.removePlayer(99).has_value());
}

TEST(Table, GetActiveAndAllPlayers) {
    Table table(4);
    table.addPlayer(Player("Alice", 0, 1000));
    table.addPlayer(Player("Bob", 1, 1000));
    table.addPlayer(Player("Carl", 2, 1000));
    table.getPlayer(1)->fold();

    EXPECT_EQ(table.getAllPlayers().size(), 3u);
    std::vector<Player*> active = table.getActivePlayers();
    ASSERT_EQ(active.size(), 2u);
    EXPECT_EQ(active[0]->name(), "Alice");
    EXPECT_EQ(active[1]->name(), "Carl");
}

TEST(Table, ResetForNewHandClearsPerHandState) {
    Table table(4);
    table.addPlayer(Player("Alice", 0, 1000));
    table.getPlayer(0)->receiveCards(Card(Suit::Spades, Rank::Ace), Card(Suit::Hearts, Rank::King));
    table.getPlayer(0)->fold();
    table.dealCommunityCards(3);
    table.addToPot(50);
    table.advanceStreet();

    table.resetForNewHand();

    EXPECT_TRUE(table.getPlayer(0)->holeCards().empty());
    EXPECT_EQ(table.getPlayer(0)->status(), PlayerStatus::Active);
    EXPECT_TRUE(table.communityCards().empty());
    EXPECT_TRUE(table.burnedCards().empty());
    EXPECT_EQ(table.totalPot(), 0);
    EXPECT_EQ(table.street(), Street::PreFlop);
    EXPECT_EQ(table.deck().remaining(), Deck::kFullDeckSize);
}

TEST(Table, DealHoleCardsGivesEveryActivePlayerTwoUniqueCards) {
    Table table(3);
    table.addPlayer(Player("Alice", 0, 1000));
    table.addPlayer(Player("Bob", 1, 1000));
    table.addPlayer(Player("Carl", 2, 1000));
    table.getPlayer(2)->fold();

    table.dealHoleCards();

    EXPECT_EQ(table.getPlayer(0)->holeCards().size(), 2u);
    EXPECT_EQ(table.getPlayer(1)->holeCards().size(), 2u);
    EXPECT_TRUE(table.getPlayer(2)->holeCards().empty());
    EXPECT_EQ(table.deck().remaining(), Deck::kFullDeckSize - 4);
}

TEST(Table, AdvanceStreetDealsFlopTurnRiverThenShowdownThenComplete) {
    Table table(2);
    EXPECT_EQ(table.street(), Street::PreFlop);

    EXPECT_EQ(table.advanceStreet(), Street::Flop);
    EXPECT_EQ(table.communityCards().size(), 3u);
    EXPECT_EQ(table.burnedCards().size(), 1u);

    EXPECT_EQ(table.advanceStreet(), Street::Turn);
    EXPECT_EQ(table.communityCards().size(), 4u);
    EXPECT_EQ(table.burnedCards().size(), 2u);

    EXPECT_EQ(table.advanceStreet(), Street::River);
    EXPECT_EQ(table.communityCards().size(), 5u);
    EXPECT_EQ(table.burnedCards().size(), 3u);

    EXPECT_EQ(table.advanceStreet(), Street::Showdown);
    EXPECT_EQ(table.communityCards().size(), 5u);
    EXPECT_EQ(table.burnedCards().size(), 3u);
    EXPECT_EQ(table.deck().remaining(), Deck::kFullDeckSize - 8);

    EXPECT_EQ(table.advanceStreet(), Street::HandComplete);
    EXPECT_THROW(table.advanceStreet(), std::logic_error);
}

TEST(Table, AdvanceStreetBurnsTheTopCardBeforeEachStreet) {
    Table table(2);
    std::vector<Card> order = {
        Card(Suit::Clubs, Rank::Two),    // burn
        Card(Suit::Spades, Rank::Ace),   // flop
        Card(Suit::Spades, Rank::King),  // flop
        Card(Suit::Spades, Rank::Queen), // flop
        Card(Suit::Clubs, Rank::Three),  // burn
        Card(Suit::Spades, Rank::Jack),  // turn
        Card(Suit::Clubs, Rank::Four),   // burn
        Card(Suit::Spades, Rank::Ten),   // river
    };
    table.deck().putOnTop(order);

    table.advanceStreet();
    table.advanceStreet();
    table.advanceStreet();

    EXPECT_EQ(table.burnedCards(), (std::vector<Card>{order[0], order[4], order[6]}));
    EXPECT_EQ(table.communityCards(), (std::vector<Card>{order[1], order[2], order[3], order[5], order[7]}));
}

TEST(Table, SetBlindsHeadsUpButtonPostsSmallBlind) {
    Table table(2);
    table.addPlayer(Player("Alice", 0, 1000));
    table.addPlayer(Player("Bob", 1, 1000));

    table.setBlinds(0, 5, 10);

    EXPECT_TRUE(table.isButton(0));
    EXPECT_EQ(table.smallBlindSeat(), 0);
    EXPECT_EQ(table.bigBlindSeat(), 1);
    EXPECT_TRUE(table.isSmallBlind(0));
    EXPECT_TRUE(table.isBigBlind(1));
}

TEST(Table, SetBlindsThreeHandedWalksForwardFromButton) {
    Table table(3);
    table.addPlayer(Player("Alice", 0, 1000));
    table.addPlayer(Player("Bob", 1, 1000));
    table.addPlayer(Player("Carl", 2, 1000));

    table.setBlinds(0, 5, 10);

    EXPECT_EQ(table.smallBlindSeat(), 1);
    EXPECT_EQ(table.bigBlindSeat(), 2);
}

TEST(Table, SetBlindsSkipsBustedSeatsBetweenButtonAndBlinds) {
    Table table(4);
    table.addPlayer(Player("Alice", 0, 1000));
    table.addPlayer(Player("Bob", 1, 1000));
    table.addPlayer(Player("Carl", 2, 1000));
    table.addPlayer(Player("Dana", 3, 1000));
    // Bust seat 1 (no chips left) so it must be skipped for blinds.
    table.getPlayer(1)->removeChips(1000);
    table.getPlayer(1)->resetForNewHand();
    ASSERT_EQ(table.getPlayer(1)->status(), PlayerStatus::SittingOut);

    table.setBlinds(0, 5, 10);

    EXPECT_EQ(table.smallBlindSeat(), 2);
    EXPECT_EQ(table.bigBlindSeat(), 3);
}

TEST(Table, SetBlindsWithOneOrNoActivePlayersLeavesBlindSeatsUnset) {
    Table table(3);
    table.addPlayer(Player("Alice", 0, 1000));
    table.addPlayer(Player("Bob", 1, 1000));
    table.getPlayer(1)->fold();

    table.setBlinds(0, 5, 10);

    EXPECT_FALSE(table.smallBlindSeat().has_value());
    EXPECT_FALSE(table.bigBlindSeat().has_value());
}

TEST(Table, RotateButtonPicksFirstActiveSeatOnFirstHand) {
    Table table(3);
    table.addPlayer(Player("Alice", 0, 1000));
    table.addPlayer(Player("Bob", 1, 1000));

    table.rotateButton();

    EXPECT_EQ(table.buttonSeat(), 0);
}

TEST(Table, RotateButtonAdvancesToNextActiveSeat) {
    Table table(3);
    table.addPlayer(Player("Alice", 0, 1000));
    table.addPlayer(Player("Bob", 1, 1000));
    table.addPlayer(Player("Carl", 2, 1000));
    table.setBlinds(0, 5, 10);

    table.rotateButton();

    EXPECT_EQ(table.buttonSeat(), 1);
}

TEST(Table, RotateButtonKeepsBlindAmounts) {
    Table table(3);
    table.addPlayer(Player("Alice", 0, 1000));
    table.addPlayer(Player("Bob", 1, 1000));
    table.addPlayer(Player("Carl", 2, 1000));
    table.setBlinds(0, 5, 10);

    table.rotateButton();

    EXPECT_EQ(table.smallBlindAmount(), 5);
    EXPECT_EQ(table.bigBlindAmount(), 10);
}

TEST(Table, SetBlindAmountsAppliesOnNextRotation) {
    Table table(3);
    table.addPlayer(Player("Alice", 0, 1000));
    table.addPlayer(Player("Bob", 1, 1000));

    table.setBlindAmounts(25, 50);
    EXPECT_FALSE(table.buttonSeat().has_value());
    table.rotateButton();

    EXPECT_EQ(table.smallBlindAmount(), 25);
    EXPECT_EQ(table.bigBlindAmount(), 50);
}

TEST(Table, FinishHandJumpsToCompleteWithoutDealing) {
    Table table(2);
    table.addPlayer(Player("Alice", 0, 1000));
    table.addPlayer(Player("Bob", 1, 1000));
    table.advanceStreet();  // flop
    table.setCurrentPlayer(1);

    table.finishHand();

    EXPECT_EQ(table.street(), Street::HandComplete);
    EXPECT_EQ(table.communityCards().size(), 3u);
    EXPECT_FALSE(table.currentPlayerSeat().has_value());
}

TEST(Table, GetNextAndPreviousActivePlayerWrapAndSkipInactive) {
    Table table(4);
    table.addPlayer(Player("Alice", 0, 1000));
    table.addPlayer(Player("Bob", 1, 1000));
    table.addPlayer(Player("Carl", 2, 1000));
    table.addPlayer(Player("Dana", 3, 1000));
    table.getPlayer(1)->fold();

    EXPECT_EQ(table.getNextActivePlayer(0), 2);
    EXPECT_EQ(table.getNextActivePlayer(3), 0);  // wraps, skipping folded seat 1
    EXPECT_EQ(table.getPreviousActivePlayer(0), 3);
    EXPECT_EQ(table.getPreviousActivePlayer(2), 0);  // wraps, skipping folded seat 1
}

TEST(Table, GetNextActivePlayerReturnsNulloptWhenNoneCanAct) {
    Table table(2);
    table.addPlayer(Player("Alice", 0, 1000));
    EXPECT_FALSE(table.getNextActivePlayer(0).has_value());
}

TEST(Table, PotHelpersClampNegativeAndAccumulate) {
    Table table(2);
    table.setPot(-5);
    EXPECT_EQ(table.totalPot(), 0);
    table.addToPot(100);
    table.addToPot(-10);
    EXPECT_EQ(table.totalPot(), 100);
}

}  // namespace
}  // namespace poker
