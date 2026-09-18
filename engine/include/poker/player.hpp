#pragma once

#include <cstdint>
#include <string>
#include <vector>

#include "poker/card.hpp"

namespace poker {

/// A player's status during the current hand. Deciding *who* controls a
/// seat (human input, an RL policy) is orchestration logic outside the
/// engine - this only tracks what the rules need to know.
enum class PlayerStatus : uint8_t {
    Active,
    Folded,
    AllIn,
    SittingOut,
};

/// One seat's player: identity, stack, hole cards, and hand status. A
/// single concrete class - there is no human/AI subclassing here, since
/// the engine never decides an action, only validates and applies one.
class Player {
public:
    Player(std::string name, int seat, int initialStack)
        : name_(std::move(name)), seat_(seat), stack_(initialStack) {}

    const std::string& name() const noexcept { return name_; }
    int seat() const noexcept { return seat_; }
    int stack() const noexcept { return stack_; }
    const std::vector<Card>& holeCards() const noexcept { return holeCards_; }
    PlayerStatus status() const noexcept { return status_; }
    int currentBet() const noexcept { return currentBet_; }

    /// Throws std::invalid_argument unless given exactly 2 cards.
    void receiveCards(Card first, Card second);
    void discardCards();

    /// Throws std::invalid_argument if `amount` is negative.
    void addChips(int amount);

    /// Removes up to `amount` chips (clamped to the current stack) and
    /// adds the same to `currentBet()`. Returns the amount actually
    /// removed. Throws std::invalid_argument if `amount` is negative.
    int removeChips(int amount);

    /// Sets `currentBet()` directly (for display/bookkeeping only - does
    /// not move chips). Throws std::invalid_argument if negative.
    void setCurrentBet(int amount);

    /// Clears hole cards and the current bet; becomes Active if the
    /// player still has chips, SittingOut otherwise (busted).
    void resetForNewHand();

    void fold() noexcept { status_ = PlayerStatus::Folded; }
    void goAllIn() noexcept { status_ = PlayerStatus::AllIn; }

    bool hasChips() const noexcept { return stack_ > 0; }

    /// True if still in the hand (not folded, not sitting out) - Active
    /// or AllIn.
    bool isActive() const noexcept {
        return status_ == PlayerStatus::Active || status_ == PlayerStatus::AllIn;
    }

    /// True if the player can still choose an action this street (Active
    /// and not yet all-in).
    bool canAct() const noexcept { return status_ == PlayerStatus::Active; }

private:
    std::string name_;
    int seat_;
    int stack_;
    std::vector<Card> holeCards_;
    PlayerStatus status_ = PlayerStatus::Active;
    int currentBet_ = 0;
};

}  // namespace poker
