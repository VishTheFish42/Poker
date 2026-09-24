#pragma once

#include <map>
#include <optional>
#include <set>
#include <vector>

#include "poker/action.hpp"
#include "poker/table.hpp"

namespace poker {

/// Manages the betting for a single street: turn order, legal-action
/// checks, and applying actions to the table's players and pot.
///
/// Blinds, once posted via `initializeBlinds()`, are treated as bets
/// already on the table - a player facing only the big blind can still
/// raise "over" it without that counting as the minimum bet being
/// re-triggered from zero.
///
/// All-in sizing follows standard no-limit rules: a full raise (>= the
/// current minimum raise) reopens the action for every player who already
/// acted; an all-in that raises by *less* than a full increment ("capped")
/// still makes already-acted players respond to the extra amount, but only
/// by calling or folding - it doesn't reopen their right to re-raise.
class BettingRound {
public:
    BettingRound(Table& table, int smallBlindAmount, int bigBlindAmount, int startSeat)
        : table_(table),
          smallBlindAmount_(smallBlindAmount),
          bigBlindAmount_(bigBlindAmount),
          startSeat_(startSeat),
          minRaiseAmount_(bigBlindAmount) {}

    /// Posts the small and big blinds from the table's configured blind
    /// seats, moving chips and updating `highestBet()`/`minRaiseAmount()`
    /// accordingly. A blind that exceeds a player's stack posts them
    /// all-in for whatever they have.
    void initializeBlinds();

    /// Chips `seatNumber` still needs to add to match the current bet.
    int getAmountToCall(int seatNumber) const;
    bool canCheck(int seatNumber) const { return getAmountToCall(seatNumber) == 0; }

    /// Validates and applies one player's action: moves chips, updates the
    /// pot, and updates turn-order bookkeeping. Throws std::invalid_argument
    /// if the action isn't legal given the current bet and the player's
    /// stack (e.g. checking with a bet to call, betting under the minimum,
    /// raising while capped by an incomplete all-in).
    void processAction(const Action& action);

    /// The seat that should act next, or nullopt once the round is
    /// complete (every active player has matched the highest bet, or only
    /// one active player remains). Marks the round complete as a side
    /// effect when it determines there's no one left to act.
    std::optional<int> getNextToAct();

    bool isRoundComplete() const noexcept { return roundComplete_; }

    const std::vector<Action>& actions() const noexcept { return actions_; }
    int highestBet() const noexcept { return highestBet_; }
    int minRaiseAmount() const noexcept { return minRaiseAmount_; }
    const std::map<int, int>& playerBetAmounts() const noexcept { return playerBetAmounts_; }

    /// True if `seatNumber` already acted and then faced an incomplete
    /// all-in raise, so it may only call or fold (not re-raise).
    bool isCapped(int seatNumber) const { return cappedSeats_.count(seatNumber) > 0; }

    /// Seats that went all-in this round, in the order they did so.
    std::vector<int> getPlayersAllIn() const;

private:
    bool computeRoundComplete();

    Table& table_;
    int smallBlindAmount_;
    int bigBlindAmount_;
    int startSeat_;
    std::vector<Action> actions_;
    std::map<int, int> playerBetAmounts_;
    bool roundComplete_ = false;
    std::optional<int> currentBettorSeat_;
    int highestBet_ = 0;
    int minRaiseAmount_;
    std::set<int> actedSeats_;
    std::set<int> cappedSeats_;
};

}  // namespace poker
