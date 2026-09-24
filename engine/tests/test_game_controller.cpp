#include "poker/game_controller.hpp"

#include <gtest/gtest.h>

#include <random>
#include <stdexcept>
#include <string>

namespace poker {
namespace {

/// Parses "As", "Td", "2c" etc. into a Card.
Card c(const std::string& text) {
    Rank rank;
    switch (text.at(0)) {
        case 'A': rank = Rank::Ace; break;
        case 'K': rank = Rank::King; break;
        case 'Q': rank = Rank::Queen; break;
        case 'J': rank = Rank::Jack; break;
        case 'T': rank = Rank::Ten; break;
        default: rank = static_cast<Rank>(text.at(0) - '0'); break;
    }
    Suit suit;
    switch (text.at(1)) {
        case 's': suit = Suit::Spades; break;
        case 'h': suit = Suit::Hearts; break;
        case 'd': suit = Suit::Diamonds; break;
        default: suit = Suit::Clubs; break;
    }
    return Card(suit, rank);
}

std::vector<Card> cards(std::initializer_list<const char*> texts) {
    std::vector<Card> result;
    for (const char* text : texts) {
        result.push_back(c(text));
    }
    return result;
}

Table makeTable(std::vector<int> stacks) {
    static const char* kNames[] = {"Alice", "Bob", "Carl", "Dana", "Eve", "Finn", "Gus", "Hal", "Ivy", "Jo"};
    Table table(static_cast<int>(stacks.size()));
    for (int seat = 0; seat < static_cast<int>(stacks.size()); ++seat) {
        table.addPlayer(Player(kNames[seat], seat, stacks[seat]));
    }
    return table;
}

int totalChips(GameController& game) {
    int total = 0;
    for (Player* player : game.table().getAllPlayers()) {
        total += player->stack();
    }
    return total + game.table().totalPot() * (game.isHandComplete() ? 0 : 1);
}

int stackOf(GameController& game, int seat) { return game.table().getPlayer(seat)->stack(); }

void act(GameController& game, ActionType type, int amount = 0) {
    ASSERT_TRUE(game.currentSeat().has_value());
    game.submitAction(Action(type, *game.currentSeat(), amount));
}

void checkDown(GameController& game) {
    while (game.phase() == HandPhase::AwaitingAction) {
        act(game, ActionType::Check);
    }
}

// 3-handed, blinds 5/10, 1000 each. First hand: button 0, SB 1, BB 2, so
// seat 0 is under the gun pre-flop and seat 1 acts first after the flop.
// Stacked cards deal seat 0, 1, 2 two each, then burn + flop, burn +
// turn, burn + river (burns written as the low clubs/diamonds below).
class GameControllerTest : public ::testing::Test {
protected:
    GameController game{makeTable({1000, 1000, 1000}), 5, 10};
};

TEST_F(GameControllerTest, NothingHappensBeforeFirstHand) {
    EXPECT_EQ(game.phase(), HandPhase::NotStarted);
    EXPECT_FALSE(game.currentSeat().has_value());
    EXPECT_FALSE(game.stepOnce());
    EXPECT_THROW(game.legalActions(), std::logic_error);
    EXPECT_THROW(game.submitAction(Action(ActionType::Fold, 0)), std::logic_error);
    EXPECT_TRUE(game.validateAction(Action(ActionType::Fold, 0)).has_value());
}

TEST(GameController, RejectsInvalidBlinds) {
    EXPECT_THROW(GameController(makeTable({100, 100}), 0, 10), std::invalid_argument);
    EXPECT_THROW(GameController(makeTable({100, 100}), 10, 5), std::invalid_argument);
}

TEST_F(GameControllerTest, StartHandPostsBlindsDealsAndPutsUnderTheGunOnTheClock) {
    game.startHand();

    EXPECT_EQ(game.handNumber(), 1);
    EXPECT_EQ(game.phase(), HandPhase::AwaitingAction);
    EXPECT_EQ(game.table().buttonSeat(), 0);
    EXPECT_EQ(game.table().smallBlindSeat(), 1);
    EXPECT_EQ(game.table().bigBlindSeat(), 2);
    EXPECT_EQ(game.currentSeat(), 0);
    EXPECT_EQ(game.table().currentPlayerSeat(), 0);
    EXPECT_EQ(game.table().street(), Street::PreFlop);
    EXPECT_EQ(game.table().totalPot(), 15);
    EXPECT_EQ(stackOf(game, 1), 995);
    EXPECT_EQ(stackOf(game, 2), 990);
    for (Player* player : game.table().getAllPlayers()) {
        EXPECT_EQ(player->holeCards().size(), 2u);
    }
    EXPECT_TRUE(game.table().communityCards().empty());
    EXPECT_EQ(game.contributions(), (std::map<int, int>{{1, 5}, {2, 10}}));
}

TEST_F(GameControllerTest, StackedCardsAreDealtInSeatOrderThenBurnsAndBoard) {
    game.startHand(cards({"As", "Ah", "Kd", "Kc", "2c", "7d", "5c", "9s", "8h", "4d", "6c", "3c", "7c", "Jh"}));

    EXPECT_EQ(game.table().getPlayer(0)->holeCards(), cards({"As", "Ah"}));
    EXPECT_EQ(game.table().getPlayer(1)->holeCards(), cards({"Kd", "Kc"}));
    EXPECT_EQ(game.table().getPlayer(2)->holeCards(), cards({"2c", "7d"}));

    act(game, ActionType::Call);
    act(game, ActionType::Call);
    act(game, ActionType::Check);
    EXPECT_EQ(game.table().communityCards(), cards({"9s", "8h", "4d"}));
    EXPECT_EQ(game.table().burnedCards(), cards({"5c"}));

    checkDown(game);
    EXPECT_EQ(game.table().communityCards(), cards({"9s", "8h", "4d", "3c", "Jh"}));
    EXPECT_EQ(game.table().burnedCards(), cards({"5c", "6c", "7c"}));
}

TEST_F(GameControllerTest, StartHandRejectsDuplicateStackedCards) {
    EXPECT_THROW(game.startHand(cards({"As", "As"})), std::invalid_argument);
}

TEST_F(GameControllerTest, CheckedDownHandGoesToShowdownAndBestHandWins) {
    game.startHand(cards({"As", "Ah", "Kd", "Kc", "2c", "7d", "5c", "9s", "8h", "4d", "6c", "3c", "7c", "Jh"}));

    act(game, ActionType::Call);   // seat 0 limps
    act(game, ActionType::Call);   // SB completes
    act(game, ActionType::Check);  // BB checks its option
    ASSERT_EQ(game.table().street(), Street::Flop);
    EXPECT_EQ(game.currentSeat(), 1);  // first left of the button
    checkDown(game);

    ASSERT_TRUE(game.isHandComplete());
    EXPECT_EQ(game.table().street(), Street::HandComplete);
    EXPECT_EQ(game.table().communityCards().size(), 5u);
    EXPECT_FALSE(game.currentSeat().has_value());
    EXPECT_EQ(game.bettingRound(), nullptr);

    ASSERT_TRUE(game.lastResult().has_value());
    EXPECT_TRUE(game.lastResult()->isShowdown());
    ASSERT_EQ(game.lastResult()->winners().size(), 1u);
    EXPECT_EQ(game.lastResult()->winners()[0].seat(), 0);
    EXPECT_EQ(game.lastResult()->totalPot(), 30);
    EXPECT_EQ(stackOf(game, 0), 1020);
    EXPECT_EQ(stackOf(game, 1), 990);
    EXPECT_EQ(stackOf(game, 2), 990);
}

TEST_F(GameControllerTest, EveryoneFoldingToTheBigBlindEndsHandWithoutShowdown) {
    game.startHand();

    act(game, ActionType::Fold);
    act(game, ActionType::Fold);

    ASSERT_TRUE(game.isHandComplete());
    EXPECT_EQ(game.table().street(), Street::HandComplete);
    EXPECT_TRUE(game.table().communityCards().empty());
    ASSERT_TRUE(game.lastResult().has_value());
    EXPECT_FALSE(game.lastResult()->isShowdown());
    EXPECT_EQ(game.lastResult()->totalPot(), 15);
    EXPECT_EQ(stackOf(game, 1), 995);
    EXPECT_EQ(stackOf(game, 2), 1005);
}

TEST_F(GameControllerTest, FoldOnLaterStreetEndsHandBeforeRiver) {
    game.startHand();
    act(game, ActionType::Call);
    act(game, ActionType::Call);
    act(game, ActionType::Check);

    act(game, ActionType::Bet, 20);  // seat 1 bets the flop
    act(game, ActionType::Fold);
    act(game, ActionType::Fold);

    ASSERT_TRUE(game.isHandComplete());
    EXPECT_EQ(game.table().communityCards().size(), 3u);
    EXPECT_EQ(stackOf(game, 1), 1020);  // 30 pre-flop pot, own 20 back
    EXPECT_EQ(totalChips(game), 3000);
}

TEST(GameController, HeadsUpButtonPostsSmallBlindAndActsFirstOnlyPreFlop) {
    GameController game(makeTable({1000, 1000}), 5, 10);
    game.startHand();

    EXPECT_EQ(game.table().buttonSeat(), 0);
    EXPECT_EQ(game.table().smallBlindSeat(), 0);
    EXPECT_EQ(game.table().bigBlindSeat(), 1);
    EXPECT_EQ(game.currentSeat(), 0);

    act(game, ActionType::Call);
    EXPECT_EQ(game.currentSeat(), 1);  // big blind's option
    act(game, ActionType::Check);

    EXPECT_EQ(game.table().street(), Street::Flop);
    EXPECT_EQ(game.currentSeat(), 1);
}

TEST_F(GameControllerTest, BigBlindGetsOptionAndCanRaiseOverOwnBlind) {
    game.startHand();
    act(game, ActionType::Call);
    act(game, ActionType::Call);

    ASSERT_EQ(game.currentSeat(), 2);
    LegalActions legal = game.legalActions();
    EXPECT_TRUE(legal.canCheck);
    EXPECT_FALSE(legal.canCall);
    EXPECT_FALSE(legal.canBet);
    EXPECT_TRUE(legal.canRaise);
    EXPECT_EQ(legal.minRaise, 10);
    EXPECT_EQ(legal.maxRaise, 990);

    act(game, ActionType::Raise, 20);

    EXPECT_EQ(game.table().street(), Street::PreFlop);
    EXPECT_EQ(game.currentSeat(), 0);
    EXPECT_EQ(game.legalActions().callAmount, 20);
}

TEST_F(GameControllerTest, LegalActionsFacingTheBigBlind) {
    game.startHand();

    LegalActions legal = game.legalActions();
    EXPECT_EQ(legal.seat, 0);
    EXPECT_TRUE(legal.canFold);
    EXPECT_FALSE(legal.canCheck);
    EXPECT_TRUE(legal.canCall);
    EXPECT_EQ(legal.callAmount, 10);
    EXPECT_FALSE(legal.canBet);
    EXPECT_TRUE(legal.canRaise);
    EXPECT_EQ(legal.minRaise, 10);
    EXPECT_EQ(legal.maxRaise, 990);
    EXPECT_TRUE(legal.canAllIn);
    EXPECT_EQ(legal.allInAmount, 1000);
}

TEST_F(GameControllerTest, LegalActionsOnUnopenedFlopOfferBetNotRaise) {
    game.startHand();
    act(game, ActionType::Call);
    act(game, ActionType::Call);
    act(game, ActionType::Check);

    LegalActions legal = game.legalActions();
    EXPECT_TRUE(legal.canCheck);
    EXPECT_FALSE(legal.canCall);
    EXPECT_TRUE(legal.canBet);
    EXPECT_EQ(legal.minBet, 10);
    EXPECT_EQ(legal.maxBet, 990);
    EXPECT_FALSE(legal.canRaise);
    EXPECT_THROW(act(game, ActionType::Raise, 10), std::invalid_argument);
}

TEST_F(GameControllerTest, OutOfTurnActionIsRejectedWithoutChangingState) {
    game.startHand();

    EXPECT_THROW(game.submitAction(Action(ActionType::Call, 1)), std::invalid_argument);
    std::optional<std::string> reason = game.validateAction(Action(ActionType::Call, 1));
    ASSERT_TRUE(reason.has_value());
    EXPECT_NE(reason->find("seat 0"), std::string::npos);

    EXPECT_EQ(game.currentSeat(), 0);
    EXPECT_EQ(game.table().totalPot(), 15);
    EXPECT_EQ(stackOf(game, 1), 995);
}

TEST_F(GameControllerTest, IllegalActionsAreRejectedWithoutChangingState) {
    game.startHand();

    EXPECT_THROW(act(game, ActionType::Check), std::invalid_argument);
    EXPECT_THROW(act(game, ActionType::Bet, 20), std::invalid_argument);     // there's a bet to call
    EXPECT_THROW(act(game, ActionType::Raise, 5), std::invalid_argument);    // under the minimum
    EXPECT_THROW(act(game, ActionType::Raise, 991), std::invalid_argument);  // more than the stack
    EXPECT_FALSE(game.validateAction(Action(ActionType::Raise, 0, 990)).has_value());

    EXPECT_EQ(game.currentSeat(), 0);
    EXPECT_EQ(stackOf(game, 0), 1000);
    EXPECT_EQ(game.table().totalPot(), 15);
}

TEST_F(GameControllerTest, StartHandWhileHandInProgressThrows) {
    game.startHand();
    EXPECT_THROW(game.startHand(), std::logic_error);
    EXPECT_EQ(game.handNumber(), 1);
}

TEST(GameController, StartHandNeedsTwoPlayersWithChips) {
    GameController lonely(makeTable({1000, 0}), 5, 10);
    EXPECT_THROW(lonely.startHand(), std::logic_error);
    EXPECT_EQ(lonely.handNumber(), 0);
    EXPECT_EQ(lonely.phase(), HandPhase::NotStarted);
}

TEST_F(GameControllerTest, ButtonAndBlindsRotateBetweenHands) {
    game.startHand();
    act(game, ActionType::Fold);
    act(game, ActionType::Fold);

    game.startHand();

    EXPECT_EQ(game.handNumber(), 2);
    EXPECT_FALSE(game.lastResult().has_value());
    EXPECT_EQ(game.table().buttonSeat(), 1);
    EXPECT_EQ(game.table().smallBlindSeat(), 2);
    EXPECT_EQ(game.table().bigBlindSeat(), 0);
    EXPECT_EQ(game.currentSeat(), 1);
    EXPECT_EQ(game.table().totalPot(), 15);
}

TEST(GameController, BustedPlayerIsSkippedForBlindsAndDealing) {
    GameController game(makeTable({1000, 0, 1000}), 5, 10);
    game.startHand();

    EXPECT_EQ(game.table().getPlayer(1)->status(), PlayerStatus::SittingOut);
    EXPECT_TRUE(game.table().getPlayer(1)->holeCards().empty());
    // Heads-up between seats 0 and 2: button 0 posts the small blind.
    EXPECT_EQ(game.table().smallBlindSeat(), 0);
    EXPECT_EQ(game.table().bigBlindSeat(), 2);

    act(game, ActionType::Fold);
    game.startHand();
    EXPECT_EQ(game.table().buttonSeat(), 2);
}

TEST_F(GameControllerTest, SingleStepModeWaitsForStepOnceBetweenStreets) {
    game.setMode(ProgressionMode::SingleStep);
    game.startHand();
    act(game, ActionType::Call);
    act(game, ActionType::Call);
    act(game, ActionType::Check);

    EXPECT_EQ(game.phase(), HandPhase::PendingAdvance);
    EXPECT_FALSE(game.currentSeat().has_value());
    EXPECT_EQ(game.table().street(), Street::PreFlop);
    EXPECT_TRUE(game.table().communityCards().empty());
    EXPECT_EQ(game.contributions(), (std::map<int, int>{{0, 10}, {1, 10}, {2, 10}}));
    EXPECT_THROW(game.submitAction(Action(ActionType::Check, 1)), std::logic_error);

    EXPECT_TRUE(game.stepOnce());

    EXPECT_EQ(game.table().street(), Street::Flop);
    EXPECT_EQ(game.table().communityCards().size(), 3u);
    EXPECT_EQ(game.phase(), HandPhase::AwaitingAction);
    EXPECT_EQ(game.currentSeat(), 1);
    EXPECT_FALSE(game.stepOnce());  // waiting on seat 1, nothing to step
    EXPECT_EQ(game.contributions(), (std::map<int, int>{{0, 10}, {1, 10}, {2, 10}}));
}

TEST_F(GameControllerTest, SingleStepAllInRunoutDealsOneStreetPerStep) {
    game.setMode(ProgressionMode::SingleStep);
    game.startHand();
    act(game, ActionType::AllIn);
    act(game, ActionType::Fold);
    act(game, ActionType::Call);  // BB calls off its remaining 990
    ASSERT_EQ(game.phase(), HandPhase::PendingAdvance);

    ASSERT_TRUE(game.stepOnce());
    EXPECT_EQ(game.table().communityCards().size(), 3u);
    EXPECT_EQ(game.phase(), HandPhase::PendingAdvance);  // nobody left to bet
    ASSERT_TRUE(game.stepOnce());
    EXPECT_EQ(game.table().communityCards().size(), 4u);
    ASSERT_TRUE(game.stepOnce());
    EXPECT_EQ(game.table().communityCards().size(), 5u);
    EXPECT_FALSE(game.isHandComplete());
    ASSERT_TRUE(game.stepOnce());
    EXPECT_TRUE(game.isHandComplete());
    EXPECT_FALSE(game.stepOnce());

    EXPECT_EQ(game.lastResult()->totalPot(), 2005);
    EXPECT_EQ(totalChips(game), 3000);
}

TEST_F(GameControllerTest, AdvanceRunsAllPendingSteps) {
    game.setMode(ProgressionMode::SingleStep);
    game.startHand();
    act(game, ActionType::AllIn);
    act(game, ActionType::AllIn);
    act(game, ActionType::AllIn);

    game.advance();

    EXPECT_TRUE(game.isHandComplete());
    EXPECT_EQ(game.table().communityCards().size(), 5u);
    EXPECT_EQ(totalChips(game), 3000);
}

TEST_F(GameControllerTest, AutoModeRunsOutTheBoardAfterAllIns) {
    game.startHand();
    act(game, ActionType::AllIn);
    act(game, ActionType::Fold);
    act(game, ActionType::Call);

    EXPECT_TRUE(game.isHandComplete());
    EXPECT_EQ(game.table().communityCards().size(), 5u);
    EXPECT_EQ(totalChips(game), 3000);
}

TEST(GameController, ShortStackAllInWinsMainPotAndSidePotGoesToNextBest) {
    GameController game(makeTable({100, 1000, 1000}), 5, 10);
    game.startHand(cards({"As", "Ah", "Kd", "Kc", "Qs", "Qh", "4c", "2c", "5d", "9h", "6c", "Js", "7c", "3d"}));

    act(game, ActionType::AllIn);      // seat 0: all-in for 100
    act(game, ActionType::Raise, 100);  // seat 1: calls to 100, raises to 200
    act(game, ActionType::Call);       // seat 2 calls 200
    ASSERT_EQ(game.table().street(), Street::Flop);
    checkDown(game);

    ASSERT_TRUE(game.isHandComplete());
    ASSERT_EQ(game.potManager().pots().size(), 2u);
    EXPECT_EQ(game.potManager().pots()[0].amount, 300);
    EXPECT_EQ(game.potManager().pots()[1].amount, 200);
    EXPECT_EQ(stackOf(game, 0), 300);   // AA wins the main pot
    EXPECT_EQ(stackOf(game, 1), 1000);  // KK wins the 200 side pot
    EXPECT_EQ(stackOf(game, 2), 800);
}

TEST_F(GameControllerTest, TiedHandsSplitThePotWithOddChipToLowestSeat) {
    // Royal flush on board: everyone plays the board.
    game.startHand(cards({"2c", "3d", "4c", "5d", "6c", "7d", "8c", "As", "Ks", "Qs", "9c", "Js", "Tc", "Ts"}));

    act(game, ActionType::Call);  // seat 0 limps
    act(game, ActionType::Fold);  // SB folds - its 5 is dead money
    act(game, ActionType::Check);
    checkDown(game);

    ASSERT_TRUE(game.isHandComplete());
    EXPECT_EQ(game.lastResult()->winners().size(), 2u);
    EXPECT_EQ(stackOf(game, 0), 1003);  // 13 of the 25 pot
    EXPECT_EQ(stackOf(game, 1), 995);
    EXPECT_EQ(stackOf(game, 2), 1002);
}

TEST(GameController, PlayerCappedByIncompleteAllInMayOnlyCallOrFold) {
    GameController game(makeTable({1000, 1000, 25}), 5, 10);
    game.startHand();

    act(game, ActionType::Raise, 10);  // seat 0 raises to 20
    act(game, ActionType::Call);       // SB calls to 20
    act(game, ActionType::AllIn);      // BB shoves to 25: a 5 raise, under the 10 minimum

    ASSERT_EQ(game.currentSeat(), 0);
    LegalActions legal = game.legalActions();
    EXPECT_TRUE(legal.canCall);
    EXPECT_EQ(legal.callAmount, 5);
    EXPECT_FALSE(legal.canRaise);
    EXPECT_FALSE(legal.canAllIn);
    EXPECT_THROW(act(game, ActionType::Raise, 10), std::invalid_argument);
    EXPECT_THROW(act(game, ActionType::AllIn), std::invalid_argument);

    act(game, ActionType::Call);
    act(game, ActionType::Call);

    EXPECT_EQ(game.table().street(), Street::Flop);
    EXPECT_EQ(game.contributions(), (std::map<int, int>{{0, 25}, {1, 25}, {2, 25}}));
}

TEST(GameController, LastPlayerWhoCanActMayNotRaiseAgainstAllIns) {
    GameController game(makeTable({2000, 1000}), 5, 10);
    game.startHand();
    act(game, ActionType::Call);
    act(game, ActionType::Check);
    act(game, ActionType::AllIn);  // BB (seat 1) shoves the flop for 990

    ASSERT_EQ(game.currentSeat(), 0);
    LegalActions legal = game.legalActions();
    EXPECT_TRUE(legal.canCall);
    EXPECT_EQ(legal.callAmount, 990);
    EXPECT_FALSE(legal.canRaise);
    EXPECT_FALSE(legal.canAllIn);

    act(game, ActionType::Call);

    EXPECT_TRUE(game.isHandComplete());
    EXPECT_EQ(game.table().communityCards().size(), 5u);
    EXPECT_EQ(totalChips(game), 3000);
}

TEST(GameController, PlayerFacingBlindsPostedAllInStillGetsToAct) {
    GameController game(makeTable({1000, 3, 6}), 5, 10);
    game.startHand();

    // Both blinds are all-in; seat 0 still owes the 6 and must decide.
    ASSERT_EQ(game.phase(), HandPhase::AwaitingAction);
    ASSERT_EQ(game.currentSeat(), 0);
    LegalActions legal = game.legalActions();
    EXPECT_EQ(legal.callAmount, 6);
    EXPECT_FALSE(legal.canRaise);

    act(game, ActionType::Call);

    EXPECT_TRUE(game.isHandComplete());
    EXPECT_EQ(game.table().communityCards().size(), 5u);
    EXPECT_EQ(totalChips(game), 1009);
}

TEST(GameController, BlindsPostedAllInWithNothingOwedRunsOutImmediately) {
    GameController game(makeTable({3, 1000}), 5, 10);
    game.startHand();

    EXPECT_TRUE(game.isHandComplete());
    EXPECT_EQ(game.table().communityCards().size(), 5u);
    EXPECT_EQ(totalChips(game), 1003);
}

// Plays many hands with random legal actions across both progression
// modes and checks invariants the rules guarantee: chips are conserved,
// every hand terminates, and everything contributed is paid back out.
TEST(GameController, RandomHandsConserveChipsAndAlwaysComplete) {
    for (unsigned int seed = 1; seed <= 20; ++seed) {
        GameController game(makeTable({500, 1200, 80, 1000, 300, 2000}), 5, 10);
        game.table().deck().seed(seed);
        std::mt19937 rng(seed);
        const int startingChips = totalChips(game);

        for (int hand = 0; hand < 60; ++hand) {
            int withChips = 0;
            for (Player* player : game.table().getAllPlayers()) {
                withChips += player->hasChips() ? 1 : 0;
            }
            if (withChips < 2) {
                break;
            }

            game.setMode(rng() % 2 ? ProgressionMode::Auto : ProgressionMode::SingleStep);
            game.startHand();

            for (int step = 0; !game.isHandComplete(); ++step) {
                ASSERT_LT(step, 1000) << "hand never finished";
                if (game.phase() == HandPhase::PendingAdvance) {
                    ASSERT_TRUE(game.stepOnce());
                    continue;
                }
                ASSERT_EQ(game.phase(), HandPhase::AwaitingAction);
                LegalActions legal = game.legalActions();
                int seat = legal.seat;

                std::vector<Action> options = {Action(ActionType::Fold, seat)};
                if (legal.canCheck) options.emplace_back(ActionType::Check, seat);
                if (legal.canCall) options.emplace_back(ActionType::Call, seat);
                if (legal.canBet) {
                    std::uniform_int_distribution<int> amount(legal.minBet, legal.maxBet);
                    options.emplace_back(ActionType::Bet, seat, amount(rng));
                }
                if (legal.canRaise) {
                    std::uniform_int_distribution<int> amount(legal.minRaise, legal.maxRaise);
                    options.emplace_back(ActionType::Raise, seat, amount(rng));
                }
                if (legal.canAllIn) options.emplace_back(ActionType::AllIn, seat);

                const Action& choice = options[rng() % options.size()];
                ASSERT_FALSE(game.validateAction(choice).has_value());
                game.submitAction(choice);
                ASSERT_EQ(totalChips(game), startingChips);
            }

            int contributed = 0;
            for (const auto& [seat, amount] : game.contributions()) {
                contributed += amount;
            }
            ASSERT_TRUE(game.lastResult().has_value());
            EXPECT_EQ(game.lastResult()->totalPot(), contributed);
            EXPECT_EQ(totalChips(game), startingChips);
            for (Player* player : game.table().getAllPlayers()) {
                EXPECT_GE(player->stack(), 0);
            }
        }
    }
}

}  // namespace
}  // namespace poker
