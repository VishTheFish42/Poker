#include "poker/pot_manager.hpp"

#include <gtest/gtest.h>

#include <algorithm>

namespace poker {
namespace {

Hand highCard(int rankValue, std::vector<int> kickers = {}) {
    return Hand(HandType::HighCard, rankValue, std::move(kickers), {});
}

TEST(PotManager, EmptyByDefault) {
    PotManager pm;
    EXPECT_EQ(pm.getTotal(), 0);
    EXPECT_TRUE(pm.pots().empty());
}

TEST(PotManager, EqualContributionsMakeOneMainPot) {
    PotManager pm;
    pm.calculatePots({{0, 100}, {1, 100}, {2, 100}});
    ASSERT_EQ(pm.pots().size(), 1u);
    EXPECT_EQ(pm.pots()[0].amount, 300);
    EXPECT_EQ(pm.getTotal(), 300);
    std::vector<int> eligible = pm.pots()[0].eligibleSeats;
    std::sort(eligible.begin(), eligible.end());
    EXPECT_EQ(eligible, (std::vector<int>{0, 1, 2}));
}

TEST(PotManager, UnevenContributionsMakeMainPlusSidePot) {
    // Seat 0 all-in for 50, seats 1 and 2 each put in 100.
    PotManager pm;
    pm.calculatePots({{0, 50}, {1, 100}, {2, 100}});

    ASSERT_EQ(pm.pots().size(), 2u);
    EXPECT_EQ(pm.pots()[0].amount, 150);  // 50 * 3 contributors
    std::vector<int> mainEligible = pm.pots()[0].eligibleSeats;
    std::sort(mainEligible.begin(), mainEligible.end());
    EXPECT_EQ(mainEligible, (std::vector<int>{0, 1, 2}));

    EXPECT_EQ(pm.pots()[1].amount, 100);  // (100-50) * 2 contributors
    std::vector<int> sideEligible = pm.pots()[1].eligibleSeats;
    std::sort(sideEligible.begin(), sideEligible.end());
    EXPECT_EQ(sideEligible, (std::vector<int>{1, 2}));

    EXPECT_EQ(pm.getTotal(), 250);
}

TEST(PotManager, ThreeDistinctAllInLevelsMakeThreePots) {
    PotManager pm;
    pm.calculatePots({{0, 20}, {1, 50}, {2, 100}});

    ASSERT_EQ(pm.pots().size(), 3u);
    EXPECT_EQ(pm.pots()[0].amount, 60);  // 20 * 3
    EXPECT_EQ(pm.pots()[1].amount, 60);  // 30 * 2
    EXPECT_EQ(pm.pots()[2].amount, 50);  // 50 * 1
    EXPECT_EQ(pm.getTotal(), 170);
}

TEST(PotManager, AwardPotsGivesSolePotToSoleContender) {
    PotManager pm;
    pm.calculatePots({{0, 100}, {1, 100}});
    std::map<int, Hand> hands{{0, highCard(14)}, {1, highCard(10)}};

    std::map<int, int> winnings = pm.awardPots(hands);
    EXPECT_EQ(winnings[0], 200);
    EXPECT_EQ(winnings[1], 0);
}

TEST(PotManager, AwardPotsExcludesFoldedPlayersFromEligibility) {
    // Seat 1 folded (not in `hands`) despite being eligible for the pot.
    PotManager pm;
    pm.calculatePots({{0, 100}, {1, 100}, {2, 100}});
    std::map<int, Hand> hands{{0, highCard(10)}, {2, highCard(14)}};

    std::map<int, int> winnings = pm.awardPots(hands);
    EXPECT_EQ(winnings[2], 300);
    EXPECT_EQ(winnings[0], 0);
    EXPECT_EQ(winnings.count(1), 0u);
}

TEST(PotManager, AwardPotsSplitsTiesEvenlyWithRemainderToLowestSeats) {
    // Equal contributions make one 99-chip pot with all three eligible;
    // seats 0 and 2 tie for the best hand, seat 1 has a weaker one, so the
    // 99 splits two ways with an odd chip left over.
    PotManager pm;
    pm.calculatePots({{0, 33}, {1, 33}, {2, 33}});
    std::map<int, Hand> hands{{0, highCard(14)}, {1, highCard(8)}, {2, highCard(14)}};

    std::map<int, int> winnings = pm.awardPots(hands);
    // 99 / 2 = 49 remainder 1 -> seat 0 (lowest-numbered winner) gets it.
    EXPECT_EQ(winnings[0], 50);
    EXPECT_EQ(winnings[2], 49);
    EXPECT_EQ(winnings[1], 0);
}

TEST(PotManager, AwardPotsHandlesSidePotWithDifferentWinnerThanMainPot) {
    // Seat 0 all-in for 50 with the best hand; seats 1/2 both put in 100
    // but seat 2 has the better hand between just the two of them.
    PotManager pm;
    pm.calculatePots({{0, 50}, {1, 100}, {2, 100}});
    std::map<int, Hand> hands{{0, highCard(14)}, {1, highCard(8)}, {2, highCard(10)}};

    std::map<int, int> winnings = pm.awardPots(hands);
    EXPECT_EQ(winnings[0], 150);  // wins the main pot (best hand, all eligible)
    EXPECT_EQ(winnings[2], 100);  // wins the side pot (best of the two eligible)
    EXPECT_EQ(winnings[1], 0);
}

}  // namespace
}  // namespace poker
