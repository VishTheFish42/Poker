#pragma once

#include <map>
#include <vector>

#include "poker/hand_evaluator.hpp"

namespace poker {

/// A single pot (main or side) with the seats eligible to win it.
struct Pot {
    int amount;
    std::vector<int> eligibleSeats;
};

/// Builds and awards the main pot and any side pots for a hand.
///
/// Side pots arise when a player is all-in for less than the largest bet.
/// Each pot tracks which seats contributed to that level and are
/// therefore eligible to win it.
class PotManager {
public:
    void reset() { pots_.clear(); }

    int getTotal() const;

    const std::vector<Pot>& pots() const noexcept { return pots_; }

    /// Builds the main pot and any side pots from each seat's total chips
    /// contributed this hand, by repeatedly peeling off the smallest
    /// all-in level: every remaining contributor puts up to that level
    /// into one pot, then the process repeats on the leftover amounts. A
    /// player who contributed less than the maximum is only eligible for
    /// pots at or below their level.
    void calculatePots(const std::map<int, int>& contributions);

    /// Determines chip winnings for each pot and returns {seat: chips
    /// won} for every seat in `hands`. For each pot, the eligible
    /// player(s) with the strongest hand win; ties split evenly, with any
    /// indivisible remainder going one chip at a time to the
    /// lowest-numbered seats among the winners. A seat absent from
    /// `hands` (folded) cannot win any pot even if listed as eligible.
    std::map<int, int> awardPots(const std::map<int, Hand>& hands) const;

private:
    std::vector<Pot> pots_;
};

}  // namespace poker
