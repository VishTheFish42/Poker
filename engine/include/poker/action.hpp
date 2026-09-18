#pragma once

#include <cstdint>

namespace poker {

enum class ActionType : uint8_t {
    Fold,
    Check,
    Call,
    Bet,
    Raise,
    AllIn,
};

/// A single player action: fold/check need no amount; call/all-in carry
/// the (engine-computed) chip amount actually moved; bet/raise carry the
/// caller's requested amount.
class Action {
public:
    /// Throws std::invalid_argument if `amount` is inconsistent with
    /// `type` (nonzero for fold/check, or negative for anything else).
    Action(ActionType type, int playerSeat, int amount = 0);

    ActionType type() const noexcept { return type_; }
    int playerSeat() const noexcept { return playerSeat_; }
    int amount() const noexcept { return amount_; }

    friend bool operator==(const Action& a, const Action& b) noexcept {
        return a.type_ == b.type_ && a.playerSeat_ == b.playerSeat_ && a.amount_ == b.amount_;
    }
    friend bool operator!=(const Action& a, const Action& b) noexcept { return !(a == b); }

private:
    ActionType type_;
    int playerSeat_;
    int amount_;
};

}  // namespace poker
