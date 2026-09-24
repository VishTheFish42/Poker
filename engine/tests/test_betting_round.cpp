#include "poker/betting_round.hpp"

#include <gtest/gtest.h>

namespace poker {
namespace {

class BettingRoundTest : public ::testing::Test {
protected:
    // 3-handed table, button seat 0, blinds 5/10, everyone starts with 1000.
    Table table{3};

    void SetUp() override {
        table.addPlayer(Player("Alice", 0, 1000));
        table.addPlayer(Player("Bob", 1, 1000));
        table.addPlayer(Player("Carl", 2, 1000));
        table.setBlinds(0, 5, 10);
        // Small blind (seat 1) acts first pre-flop in a 3-handed game
        // after the big blind (seat 2) - UTG is seat 0 here for
        // simplicity since blinds were posted by seats 1 and 2.
    }
};

TEST_F(BettingRoundTest, InitializeBlindsPostsFromStacksAndSetsHighestBet) {
    BettingRound round(table, 5, 10, 0);
    round.initializeBlinds();

    EXPECT_EQ(table.getPlayer(1)->stack(), 995);
    EXPECT_EQ(table.getPlayer(2)->stack(), 990);
    EXPECT_EQ(round.highestBet(), 10);
    EXPECT_EQ(round.minRaiseAmount(), 10);
    EXPECT_EQ(round.getAmountToCall(0), 10);
    EXPECT_EQ(round.getAmountToCall(1), 5);
    EXPECT_EQ(round.getAmountToCall(2), 0);
    EXPECT_TRUE(round.canCheck(2));
    EXPECT_FALSE(round.canCheck(0));
}

TEST_F(BettingRoundTest, InitializeBlindsPostsShortStackAllIn) {
    table.removePlayer(1);
    table.addPlayer(Player("Bob", 1, 3));  // shorter than the 5 small blind
    table.setBlinds(0, 5, 10);

    BettingRound round(table, 5, 10, 0);
    round.initializeBlinds();

    EXPECT_EQ(table.getPlayer(1)->stack(), 0);
    EXPECT_EQ(table.getPlayer(1)->status(), PlayerStatus::AllIn);
    EXPECT_EQ(round.getAmountToCall(1), 7);  // highest bet 10, posted only 3
}

TEST_F(BettingRoundTest, CheckWithAmountDueThrows) {
    BettingRound round(table, 5, 10, 0);
    round.initializeBlinds();
    EXPECT_THROW(round.processAction(Action(ActionType::Check, 0)), std::invalid_argument);
}

TEST_F(BettingRoundTest, CallMovesChipsAndMatchesHighestBet) {
    BettingRound round(table, 5, 10, 0);
    round.initializeBlinds();

    round.processAction(Action(ActionType::Call, 0, 0));

    EXPECT_EQ(table.getPlayer(0)->stack(), 990);
    EXPECT_EQ(round.playerBetAmounts().at(0), 10);
    EXPECT_EQ(table.totalPot(), 25);  // 5 (SB) + 10 (BB) + 10 (call)
}

TEST_F(BettingRoundTest, CallExceedingStackThrows) {
    table.removePlayer(0);
    table.addPlayer(Player("Alice", 0, 3));
    BettingRound round(table, 5, 10, 0);
    round.initializeBlinds();

    EXPECT_THROW(round.processAction(Action(ActionType::Call, 0, 0)), std::invalid_argument);
}

TEST_F(BettingRoundTest, BetWhenFacingACallThrows) {
    BettingRound round(table, 5, 10, 0);
    round.initializeBlinds();
    EXPECT_THROW(round.processAction(Action(ActionType::Bet, 0, 50)), std::invalid_argument);
}

TEST_F(BettingRoundTest, BetBelowMinimumThrows) {
    // Big blind checks its option, reopening a bet-legal state for the
    // round... actually simplest: use a fresh round with no blinds so
    // seat 0 opens the action with BET directly.
    Table freshTable{2};
    freshTable.addPlayer(Player("Alice", 0, 1000));
    freshTable.addPlayer(Player("Bob", 1, 1000));
    BettingRound round(freshTable, 5, 10, 0);
    EXPECT_THROW(round.processAction(Action(ActionType::Bet, 0, 5)), std::invalid_argument);
}

TEST_F(BettingRoundTest, RaiseBelowMinimumThrows) {
    BettingRound round(table, 5, 10, 0);
    round.initializeBlinds();
    EXPECT_THROW(round.processAction(Action(ActionType::Raise, 0, 5)), std::invalid_argument);
}

TEST_F(BettingRoundTest, RaiseExceedingStackThrows) {
    table.removePlayer(0);
    table.addPlayer(Player("Alice", 0, 15));
    BettingRound round(table, 5, 10, 0);
    round.initializeBlinds();
    // To call 10 and raise 20 needs 30, but the stack is only 15.
    EXPECT_THROW(round.processAction(Action(ActionType::Raise, 0, 20)), std::invalid_argument);
}

TEST_F(BettingRoundTest, FullRaiseReopensActionAndUpdatesMinRaise) {
    BettingRound round(table, 5, 10, 0);
    round.initializeBlinds();

    round.processAction(Action(ActionType::Raise, 0, 20));  // calls 10, raises 20 -> bet to 30

    EXPECT_EQ(round.highestBet(), 30);
    EXPECT_EQ(round.minRaiseAmount(), 20);
    EXPECT_EQ(table.getPlayer(0)->stack(), 970);
    EXPECT_EQ(round.getAmountToCall(1), 25);
    EXPECT_EQ(round.getAmountToCall(2), 20);
}

TEST_F(BettingRoundTest, FoldMarksPlayerFolded) {
    BettingRound round(table, 5, 10, 0);
    round.initializeBlinds();
    round.processAction(Action(ActionType::Fold, 0));
    EXPECT_EQ(table.getPlayer(0)->status(), PlayerStatus::Folded);
}

TEST_F(BettingRoundTest, AllInBelowCurrentBetDoesNotReopenAction) {
    // Shrink seat 2's stack so an all-in after facing the big blind is
    // for less than a full raise increment.
    table.removePlayer(2);
    table.addPlayer(Player("Carl", 2, 14));
    table.setBlinds(0, 5, 10);
    BettingRound round(table, 5, 10, 0);
    round.initializeBlinds();

    round.processAction(Action(ActionType::Call, 0, 0));   // seat 0 calls the BB (10)
    round.processAction(Action(ActionType::Call, 1, 0));   // SB completes to 10
    round.processAction(Action(ActionType::AllIn, 2, 0));  // BB shoves remaining 4 -> total 14

    EXPECT_EQ(round.highestBet(), 14);
    EXPECT_EQ(round.minRaiseAmount(), 10);  // unchanged - incomplete raise
    EXPECT_TRUE(round.getPlayersAllIn() == std::vector<int>{2});
}

TEST_F(BettingRoundTest, IncompleteAllInRaiseCapsAlreadyActedSeats) {
    // Seat 1 has just enough to raise seat 0's bet-to-30 by 10 (less than
    // the 20 minimum), which must cap seat 0's right to re-raise without
    // capping seat 2 (who hasn't acted at this bet level yet).
    table.removePlayer(1);
    table.addPlayer(Player("Bob", 1, 40));
    table.setBlinds(0, 5, 10);
    BettingRound round(table, 5, 10, 0);
    round.initializeBlinds();

    round.processAction(Action(ActionType::Raise, 0, 20));  // seat 0: calls 10, raises 20 -> bet 30 (full raise)
    round.processAction(Action(ActionType::AllIn, 1, 0));   // seat 1: 35 left -> total 40, raise size 10 < min raise 20

    EXPECT_EQ(round.highestBet(), 40);
    EXPECT_EQ(round.minRaiseAmount(), 20);  // unchanged - incomplete raise doesn't update it
    EXPECT_TRUE(round.isCapped(0));
    EXPECT_FALSE(round.isCapped(2));
    EXPECT_THROW(round.processAction(Action(ActionType::Raise, 0, 50)), std::invalid_argument);
    EXPECT_NO_THROW(round.processAction(Action(ActionType::Call, 0, 0)));
}

class BettingRoundTurnOrderTest : public ::testing::Test {
protected:
    Table table{3};

    void SetUp() override {
        table.addPlayer(Player("Alice", 0, 1000));
        table.addPlayer(Player("Bob", 1, 1000));
        table.addPlayer(Player("Carl", 2, 1000));
        table.setBlinds(0, 5, 10);
    }
};

TEST_F(BettingRoundTurnOrderTest, GetNextToActStartsAtStartSeat) {
    BettingRound round(table, 5, 10, 0);
    round.initializeBlinds();
    EXPECT_EQ(round.getNextToAct(), 0);
}

TEST_F(BettingRoundTurnOrderTest, RoundCompletesWhenEveryoneHasMatchedTheBet) {
    BettingRound round(table, 5, 10, 0);
    round.initializeBlinds();

    ASSERT_EQ(round.getNextToAct(), 0);
    round.processAction(Action(ActionType::Call, 0, 0));

    ASSERT_EQ(round.getNextToAct(), 1);
    round.processAction(Action(ActionType::Call, 1, 0));

    ASSERT_EQ(round.getNextToAct(), 2);
    round.processAction(Action(ActionType::Check, 2));

    EXPECT_FALSE(round.getNextToAct().has_value());
    EXPECT_TRUE(round.isRoundComplete());
}

TEST_F(BettingRoundTurnOrderTest, FoldingDownToOnePlayerCompletesRound) {
    BettingRound round(table, 5, 10, 0);
    round.initializeBlinds();

    round.processAction(Action(ActionType::Fold, 0));
    round.processAction(Action(ActionType::Fold, 1));

    EXPECT_FALSE(round.getNextToAct().has_value());
    EXPECT_TRUE(round.isRoundComplete());
}

}  // namespace
}  // namespace poker
