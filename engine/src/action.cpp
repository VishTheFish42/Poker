#include "poker/action.hpp"

#include <stdexcept>

namespace poker {

Action::Action(ActionType type, int playerSeat, int amount)
    : type_(type), playerSeat_(playerSeat), amount_(amount) {
    if ((type == ActionType::Fold || type == ActionType::Check) && amount != 0) {
        throw std::invalid_argument("Fold/Check actions must have amount=0");
    }
    if (type != ActionType::Fold && type != ActionType::Check && amount < 0) {
        throw std::invalid_argument("Action amount cannot be negative");
    }
}

}  // namespace poker
