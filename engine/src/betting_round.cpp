#include "poker/betting_round.hpp"

#include <algorithm>
#include <stdexcept>

namespace poker {

void BettingRound::initializeBlinds() {
    if (std::optional<int> sbSeat = table_.smallBlindSeat()) {
        if (Player* sb = table_.getPlayer(*sbSeat)) {
            int amount = std::min(smallBlindAmount_, sb->stack());
            int actual = sb->removeChips(amount);
            playerBetAmounts_[*sbSeat] = actual;
            table_.addToPot(actual);
            highestBet_ = actual;
            if (sb->stack() == 0) {
                sb->goAllIn();
            }
        }
    }

    if (std::optional<int> bbSeat = table_.bigBlindSeat()) {
        if (Player* bb = table_.getPlayer(*bbSeat)) {
            int amount = std::min(bigBlindAmount_, bb->stack());
            int actual = bb->removeChips(amount);
            playerBetAmounts_[*bbSeat] = actual;
            table_.addToPot(actual);
            highestBet_ = std::max(highestBet_, actual);
            minRaiseAmount_ = actual;
            if (bb->stack() == 0) {
                bb->goAllIn();
            }
        }
    }
}

int BettingRound::getAmountToCall(int seatNumber) const {
    auto it = playerBetAmounts_.find(seatNumber);
    int currentBet = it != playerBetAmounts_.end() ? it->second : 0;
    return std::max(0, highestBet_ - currentBet);
}

void BettingRound::processAction(const Action& action) {
    Player* player = table_.getPlayer(action.playerSeat());
    if (!player) {
        throw std::invalid_argument("No player in that seat");
    }

    int amountToCall = getAmountToCall(action.playerSeat());

    switch (action.type()) {
        case ActionType::Check:
            if (amountToCall > 0) {
                throw std::invalid_argument("Cannot check with an amount to call");
            }
            break;
        case ActionType::Fold:
            break;
        case ActionType::Call:
            if (amountToCall > player->stack()) {
                throw std::invalid_argument("Cannot call with an insufficient stack");
            }
            break;
        case ActionType::Bet:
            if (amountToCall > 0) {
                throw std::invalid_argument("Cannot bet when there's an amount to call");
            }
            if (action.amount() > player->stack()) {
                throw std::invalid_argument("Cannot bet more than the player's stack");
            }
            if (action.amount() < minRaiseAmount_) {
                throw std::invalid_argument("Bet is less than the minimum bet");
            }
            break;
        case ActionType::Raise:
            if (cappedSeats_.count(action.playerSeat()) > 0) {
                throw std::invalid_argument(
                    "Cannot raise: facing an incomplete all-in raise, may only call or fold");
            }
            if (amountToCall + action.amount() > player->stack()) {
                throw std::invalid_argument("Cannot raise with an insufficient stack");
            }
            if (action.amount() < minRaiseAmount_) {
                throw std::invalid_argument("Raise is less than the minimum raise");
            }
            break;
        case ActionType::AllIn:
            break;  // Always valid - bets/calls whatever remains of the stack.
    }

    actions_.push_back(action);
    table_.setCurrentPlayer(action.playerSeat());
    currentBettorSeat_ = action.playerSeat();

    switch (action.type()) {
        case ActionType::Fold:
            player->fold();
            actedSeats_.insert(action.playerSeat());
            break;

        case ActionType::Check:
            actedSeats_.insert(action.playerSeat());
            break;

        case ActionType::Call: {
            int chipsAdded = player->removeChips(amountToCall);
            playerBetAmounts_[action.playerSeat()] += chipsAdded;
            table_.addToPot(chipsAdded);
            actedSeats_.insert(action.playerSeat());
            break;
        }

        case ActionType::Bet: {
            int chipsAdded = player->removeChips(action.amount());
            playerBetAmounts_[action.playerSeat()] += chipsAdded;
            table_.addToPot(chipsAdded);
            // BET is only legal when amountToCall is 0, so this player's
            // existing bet already equals the old highest bet (e.g. the
            // big blind's option to raise over its own posted blind).
            highestBet_ += chipsAdded;
            minRaiseAmount_ = chipsAdded;
            actedSeats_ = {action.playerSeat()};
            cappedSeats_.clear();
            break;
        }

        case ActionType::Raise: {
            int callAmount = player->removeChips(amountToCall);
            int raiseAmount = player->removeChips(action.amount());
            playerBetAmounts_[action.playerSeat()] += callAmount + raiseAmount;
            table_.addToPot(callAmount + raiseAmount);
            highestBet_ += action.amount();
            minRaiseAmount_ = action.amount();
            actedSeats_ = {action.playerSeat()};
            cappedSeats_.clear();
            break;
        }

        case ActionType::AllIn: {
            int chipsAdded = player->removeChips(player->stack());
            int newTotal = playerBetAmounts_[action.playerSeat()] + chipsAdded;
            playerBetAmounts_[action.playerSeat()] = newTotal;
            table_.addToPot(chipsAdded);
            player->goAllIn();

            if (newTotal > highestBet_) {
                int raiseSize = newTotal - highestBet_;
                if (raiseSize >= minRaiseAmount_) {
                    minRaiseAmount_ = raiseSize;
                    cappedSeats_.clear();
                } else {
                    for (int seat : actedSeats_) {
                        if (seat != action.playerSeat()) {
                            cappedSeats_.insert(seat);
                        }
                    }
                }
                highestBet_ = newTotal;
                actedSeats_ = {action.playerSeat()};
            } else {
                actedSeats_.insert(action.playerSeat());
            }
            break;
        }
    }

    // Any action that exhausts a player's stack makes them all-in,
    // regardless of which action type was used to get there.
    if (action.type() != ActionType::Fold && player->stack() == 0) {
        player->goAllIn();
    }
}

std::optional<int> BettingRound::getNextToAct() {
    if (table_.getActivePlayers().empty()) {
        roundComplete_ = true;
        return std::nullopt;
    }

    if (currentBettorSeat_.has_value() && computeRoundComplete()) {
        roundComplete_ = true;
        return std::nullopt;
    }

    int searchFrom;
    if (!currentBettorSeat_.has_value()) {
        searchFrom = startSeat_;
    } else {
        std::optional<int> next = table_.getNextActivePlayer(*currentBettorSeat_);
        if (!next.has_value()) {
            roundComplete_ = true;
            return std::nullopt;
        }
        searchFrom = *next;
    }

    for (int i = 0; i < table_.numSeats(); ++i) {
        int checkSeat = (searchFrom + i) % table_.numSeats();
        Player* player = table_.getPlayer(checkSeat);
        if (player && player->canAct()) {
            return checkSeat;
        }
    }

    roundComplete_ = true;
    return std::nullopt;
}

bool BettingRound::computeRoundComplete() {
    std::vector<Player*> active = table_.getActivePlayers();
    if (active.size() <= 1) {
        return true;
    }

    for (Player* player : active) {
        if (player->status() == PlayerStatus::AllIn) {
            continue;
        }
        if (actedSeats_.count(player->seat()) == 0) {
            return false;
        }
        auto it = playerBetAmounts_.find(player->seat());
        int betAmount = it != playerBetAmounts_.end() ? it->second : 0;
        if (betAmount < highestBet_) {
            return false;
        }
    }
    return true;
}

std::vector<int> BettingRound::getPlayersAllIn() const {
    std::vector<int> seats;
    for (const Action& action : actions_) {
        if (action.type() == ActionType::AllIn) {
            seats.push_back(action.playerSeat());
        }
    }
    return seats;
}

}  // namespace poker
