#include "poker/showdown.hpp"

#include <gtest/gtest.h>

namespace poker {
namespace {

TEST(Showdown, NoActivePlayersReturnsEmptyResult) {
    PotManager pm;
    ShowdownResult result = Showdown::resolve({}, {}, pm);
    EXPECT_TRUE(result.playerResults().empty());
    EXPECT_FALSE(result.isShowdown());
}

TEST(Showdown, SolePlayerWinsWithoutShowdownAndNoBoardRequired) {
    Player alice("Alice", 0, 1000);
    alice.receiveCards(Card(Suit::Spades, Rank::Ace), Card(Suit::Hearts, Rank::King));

    PotManager pm;
    pm.calculatePots({{0, 40}});

    ShowdownResult result = Showdown::resolve({&alice}, {}, pm);

    EXPECT_FALSE(result.isShowdown());
    ASSERT_EQ(result.playerResults().size(), 1u);
    const PlayerResult& r = result.playerResults()[0];
    EXPECT_EQ(r.seat(), 0);
    EXPECT_EQ(r.chipsWon(), 40);
    EXPECT_FALSE(r.bestHand().has_value());
    EXPECT_EQ(alice.stack(), 1040);
}

TEST(Showdown, TwoPlayerShowdownAwardsBestHandAndCreditsStack) {
    Player alice("Alice", 0, 1000);
    alice.receiveCards(Card(Suit::Spades, Rank::Ace), Card(Suit::Hearts, Rank::Ace));
    Player bob("Bob", 1, 1000);
    bob.receiveCards(Card(Suit::Clubs, Rank::Two), Card(Suit::Diamonds, Rank::Seven));

    std::vector<Card> board = {
        Card(Suit::Spades, Rank::King), Card(Suit::Hearts, Rank::Queen), Card(Suit::Clubs, Rank::Jack),
        Card(Suit::Diamonds, Rank::Four), Card(Suit::Spades, Rank::Nine),
    };

    PotManager pm;
    pm.calculatePots({{0, 100}, {1, 100}});

    ShowdownResult result = Showdown::resolve({&alice, &bob}, board, pm);

    EXPECT_TRUE(result.isShowdown());
    ASSERT_EQ(result.playerResults().size(), 2u);

    const PlayerResult* aliceResult = nullptr;
    const PlayerResult* bobResult = nullptr;
    for (const PlayerResult& r : result.playerResults()) {
        if (r.seat() == 0) aliceResult = &r;
        if (r.seat() == 1) bobResult = &r;
    }
    ASSERT_NE(aliceResult, nullptr);
    ASSERT_NE(bobResult, nullptr);

    EXPECT_TRUE(aliceResult->bestHand().has_value());
    EXPECT_EQ(aliceResult->bestHand()->type(), HandType::OnePair);  // pocket aces
    EXPECT_EQ(aliceResult->chipsWon(), 200);
    EXPECT_EQ(bobResult->chipsWon(), 0);
    EXPECT_EQ(alice.stack(), 1200);
    EXPECT_EQ(bob.stack(), 1000);
}

TEST(Showdown, ShowdownWithWrongBoardSizeThrows) {
    Player alice("Alice", 0, 1000);
    alice.receiveCards(Card(Suit::Spades, Rank::Ace), Card(Suit::Hearts, Rank::Ace));
    Player bob("Bob", 1, 1000);
    bob.receiveCards(Card(Suit::Clubs, Rank::Two), Card(Suit::Diamonds, Rank::Seven));

    PotManager pm;
    pm.calculatePots({{0, 100}, {1, 100}});

    EXPECT_THROW(Showdown::resolve({&alice, &bob}, {}, pm), std::invalid_argument);
}

TEST(Showdown, ResultWinnersAndTotalPotAccessors) {
    Player alice("Alice", 0, 1000);
    alice.receiveCards(Card(Suit::Spades, Rank::Ace), Card(Suit::Hearts, Rank::Ace));
    Player bob("Bob", 1, 1000);
    bob.receiveCards(Card(Suit::Clubs, Rank::Two), Card(Suit::Diamonds, Rank::Seven));

    std::vector<Card> board = {
        Card(Suit::Spades, Rank::King), Card(Suit::Hearts, Rank::Queen), Card(Suit::Clubs, Rank::Jack),
        Card(Suit::Diamonds, Rank::Four), Card(Suit::Spades, Rank::Nine),
    };

    PotManager pm;
    pm.calculatePots({{0, 100}, {1, 100}});

    ShowdownResult result = Showdown::resolve({&alice, &bob}, board, pm);

    EXPECT_EQ(result.totalPot(), 200);
    std::vector<PlayerResult> winners = result.winners();
    ASSERT_EQ(winners.size(), 1u);
    EXPECT_EQ(winners[0].seat(), 0);
}

}  // namespace
}  // namespace poker
