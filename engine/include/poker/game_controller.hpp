#pragma once

#include <cstdint>
#include <map>
#include <optional>
#include <string>
#include <vector>

#include "poker/action.hpp"
#include "poker/betting_round.hpp"
#include "poker/card.hpp"
#include "poker/pot_manager.hpp"
#include "poker/showdown.hpp"
#include "poker/table.hpp"

namespace poker {

/// How the controller moves past points in a hand that need no player
/// decision (closing a street, dealing the next one, an all-in runout,
/// the showdown).
enum class ProgressionMode : uint8_t {
    /// Every such transition happens immediately inside `startHand()` /
    /// `submitAction()`, so the controller is only ever waiting on a
    /// player's action or finished with the hand.
    Auto,
    /// Transitions wait for the caller to invoke `stepOnce()` (one at a
    /// time) or `advance()` (all of them), so a UI or AI loop can pace
    /// the hand.
    SingleStep,
};

/// Where the current hand stands.
enum class HandPhase : uint8_t {
    /// No hand has been started yet.
    NotStarted,
    /// `currentSeat()` must act via `submitAction()`.
    AwaitingAction,
    /// Betting on the current street is settled; `stepOnce()` deals the
    /// next street or resolves the hand.
    PendingAdvance,
    /// The hand is resolved (`lastResult()` is set); `startHand()` begins
    /// the next one.
    HandComplete,
};

/// What the seat on the clock may legally do right now, with the amount
/// bounds needed to build a legal action.
struct LegalActions {
    int seat = -1;
    bool canFold = false;
    bool canCheck = false;
    bool canCall = false;
    /// Chips needed to match the current bet (0 if the seat can check).
    int callAmount = 0;
    /// Opening the betting on a street with no bet yet. `Bet` amounts are
    /// the chips put in.
    bool canBet = false;
    int minBet = 0;
    int maxBet = 0;
    /// Raising an existing bet (including the big blind). `Raise` amounts
    /// are "raise by" - chips added on top of `callAmount`.
    bool canRaise = false;
    int minRaise = 0;
    int maxRaise = 0;
    /// Pushing the whole stack in. Not offered when the stack exceeds the
    /// call but raising isn't allowed (capped by an incomplete all-in, or
    /// no opponent left who could respond) - call instead.
    bool canAllIn = false;
    int allInAmount = 0;
};

/// Runs hands of Texas Hold'em on a table it owns: button rotation, blind
/// posting, dealing, one `BettingRound` per street, all-in runouts, and
/// the showdown via `PotManager`/`Showdown`.
///
/// The controller never decides an action - the caller submits each one
/// for the seat on the clock (`currentSeat()`), and the controller checks
/// it against turn order and `legalActions()` before applying it.
///
/// Deal order: two consecutive cards to each player in seat order
/// (starting from seat 0), then burn + flop, burn + turn, burn + river.
///
/// Not copyable or movable: each street's `BettingRound` refers to the
/// owned table by reference.
class GameController {
public:
    /// Throws std::invalid_argument unless 0 < smallBlind <= bigBlind.
    GameController(Table table, int smallBlindAmount, int bigBlindAmount,
                   ProgressionMode mode = ProgressionMode::Auto);

    GameController(const GameController&) = delete;
    GameController& operator=(const GameController&) = delete;

    /// Seat players, remove them, or seed the deck between hands through
    /// this. Changing it mid-hand is unsupported.
    Table& table() noexcept { return table_; }
    const Table& table() const noexcept { return table_; }

    int smallBlindAmount() const noexcept { return smallBlindAmount_; }
    int bigBlindAmount() const noexcept { return bigBlindAmount_; }

    ProgressionMode mode() const noexcept { return mode_; }
    /// Takes effect at the next action or hand; switching to Auto while a
    /// transition is pending doesn't run it - call `advance()` for that.
    void setMode(ProgressionMode mode) noexcept { mode_ = mode; }

    HandPhase phase() const noexcept { return phase_; }
    bool isHandComplete() const noexcept { return phase_ == HandPhase::HandComplete; }

    /// 1 for the first hand, incremented by each `startHand()`.
    int handNumber() const noexcept { return handNumber_; }

    /// The seat that must act, or nullopt unless the phase is
    /// AwaitingAction.
    std::optional<int> currentSeat() const noexcept;

    /// Starts a new hand: resets the table, rotates the button, shuffles,
    /// deals hole cards, posts blinds, and opens pre-flop betting.
    /// `stackedCards`, if given, are dealt first in that order (see the
    /// class comment for the deal order) with the rest of the deck
    /// shuffled beneath them. Throws std::logic_error if a hand is in
    /// progress or fewer than 2 seated players have chips, and
    /// std::invalid_argument if `stackedCards` repeats a card.
    void startHand(const std::vector<Card>& stackedCards = {});

    /// Throws std::logic_error unless the phase is AwaitingAction.
    LegalActions legalActions() const;

    /// Why `action` would be illegal right now, or nullopt if it's legal.
    /// Never changes state. Call and all-in amounts are ignored (the
    /// engine computes them); bet/raise amounts must be within
    /// `legalActions()`'s bounds.
    std::optional<std::string> validateAction(const Action& action) const;

    /// Applies `action` for the seat on the clock and moves the turn on.
    /// In Auto mode, also runs any transitions that follow. Throws
    /// std::logic_error unless the phase is AwaitingAction, and
    /// std::invalid_argument (with `validateAction()`'s reason) if the
    /// action is illegal - in both cases nothing changes.
    void submitAction(const Action& action);

    /// Runs one pending transition: deals the next street (opening its
    /// betting, if anyone can still bet), or resolves the hand once the
    /// river is settled or only one player is left. Returns false, doing
    /// nothing, unless the phase is PendingAdvance.
    bool stepOnce();

    /// Calls `stepOnce()` until a player must act or the hand is complete.
    void advance();

    /// The current street's betting, or nullptr between streets and hands.
    const BettingRound* bettingRound() const noexcept { return round_ ? &*round_ : nullptr; }

    /// Chips each seat has put into the pot this hand, blinds included.
    std::map<int, int> contributions() const;

    /// The main pot and side pots, calculated when the hand is resolved.
    const PotManager& potManager() const noexcept { return potManager_; }

    /// The outcome of the most recently completed hand; cleared by
    /// `startHand()`.
    const std::optional<ShowdownResult>& lastResult() const noexcept { return lastResult_; }

private:
    void openBettingRound();
    bool bettingNeeded() const;
    void moveTurnOn();
    void collectRoundContributions();
    void resolveHand();

    Table table_;
    int smallBlindAmount_;
    int bigBlindAmount_;
    ProgressionMode mode_;
    HandPhase phase_ = HandPhase::NotStarted;
    int handNumber_ = 0;
    std::optional<BettingRound> round_;
    std::map<int, int> contributions_;  // from streets already closed
    PotManager potManager_;
    std::optional<ShowdownResult> lastResult_;
};

}  // namespace poker
