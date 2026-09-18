#include "poker/player.hpp"

#include <algorithm>
#include <stdexcept>

namespace poker {

void Player::receiveCards(Card first, Card second) {
    holeCards_ = {first, second};
}

void Player::discardCards() {
    holeCards_.clear();
}

void Player::addChips(int amount) {
    if (amount < 0) {
        throw std::invalid_argument("Cannot add negative chips.");
    }
    stack_ += amount;
}

int Player::removeChips(int amount) {
    if (amount < 0) {
        throw std::invalid_argument("Cannot remove negative chips.");
    }
    int actual = std::min(amount, stack_);
    stack_ -= actual;
    currentBet_ += actual;
    return actual;
}

void Player::setCurrentBet(int amount) {
    if (amount < 0) {
        throw std::invalid_argument("Current bet cannot be negative.");
    }
    currentBet_ = amount;
}

void Player::resetForNewHand() {
    discardCards();
    status_ = hasChips() ? PlayerStatus::Active : PlayerStatus::SittingOut;
    currentBet_ = 0;
}

}  // namespace poker
