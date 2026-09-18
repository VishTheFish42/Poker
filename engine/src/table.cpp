#include "poker/table.hpp"

#include <stdexcept>

namespace poker {

int streetNumber(Street street) noexcept {
    switch (street) {
        case Street::PreFlop:
            return 0;
        case Street::Flop:
            return 1;
        case Street::Turn:
            return 2;
        case Street::River:
            return 3;
        case Street::Showdown:
            return 4;
        case Street::HandComplete:
            return -1;
    }
    return -1;
}

Table::Table(int numSeats) : numSeats_(numSeats) {
    if (numSeats < 2 || numSeats > kMaxPlayers) {
        throw std::invalid_argument("Table must have 2-10 seats");
    }
    players_.resize(numSeats_);
    markers_.resize(numSeats_);
}

void Table::addPlayer(Player player) {
    int seat = player.seat();
    if (seat < 0 || seat >= numSeats_) {
        throw std::invalid_argument("Invalid seat number");
    }
    if (players_[seat].has_value()) {
        throw std::invalid_argument("Seat is already occupied");
    }
    players_[seat] = std::move(player);
}

std::optional<Player> Table::removePlayer(int seatNumber) {
    if (seatNumber < 0 || seatNumber >= numSeats_) {
        return std::nullopt;
    }
    std::optional<Player> removed = std::move(players_[seatNumber]);
    players_[seatNumber].reset();
    return removed;
}

Player* Table::getPlayer(int seatNumber) noexcept {
    if (seatNumber < 0 || seatNumber >= numSeats_ || !players_[seatNumber].has_value()) {
        return nullptr;
    }
    return &*players_[seatNumber];
}

const Player* Table::getPlayer(int seatNumber) const noexcept {
    if (seatNumber < 0 || seatNumber >= numSeats_ || !players_[seatNumber].has_value()) {
        return nullptr;
    }
    return &*players_[seatNumber];
}

std::vector<Player*> Table::getActivePlayers() {
    std::vector<Player*> result;
    for (auto& seat : players_) {
        if (seat.has_value() && seat->isActive()) {
            result.push_back(&*seat);
        }
    }
    return result;
}

std::vector<Player*> Table::getAllPlayers() {
    std::vector<Player*> result;
    for (auto& seat : players_) {
        if (seat.has_value()) {
            result.push_back(&*seat);
        }
    }
    return result;
}

void Table::resetForNewHand() {
    for (auto& seat : players_) {
        if (seat.has_value()) {
            seat->resetForNewHand();
        }
    }
    deck_.reset();
    communityCards_.clear();
    street_ = Street::PreFlop;
    currentPlayerSeat_.reset();
    totalPot_ = 0;
}

int Table::firstActiveSeat() const {
    for (int i = 0; i < numSeats_; ++i) {
        if (players_[i].has_value() && players_[i]->canAct()) {
            return i;
        }
    }
    return 0;
}

void Table::setBlinds(int buttonSeat, int smallBlindAmount, int bigBlindAmount) {
    for (auto& marker : markers_) {
        marker = SeatMarkers{};
    }

    buttonSeat_ = buttonSeat;
    markers_[buttonSeat].isButton = true;
    smallBlindAmount_ = smallBlindAmount;
    bigBlindAmount_ = bigBlindAmount;

    std::vector<Player*> active = getActivePlayers();
    if (active.size() <= 1) {
        smallBlindSeat_.reset();
        bigBlindSeat_.reset();
        return;
    }

    if (active.size() == 2) {
        int other = buttonSeat;
        for (Player* p : active) {
            if (p->seat() != buttonSeat) {
                other = p->seat();
                break;
            }
        }
        smallBlindSeat_ = buttonSeat;
        bigBlindSeat_ = other;
    } else {
        smallBlindSeat_ = getNextActivePlayer(buttonSeat);
        bigBlindSeat_ = getNextActivePlayer(*smallBlindSeat_);
    }

    markers_[*smallBlindSeat_].isSmallBlind = true;
    markers_[*bigBlindSeat_].isBigBlind = true;
}

void Table::rotateButton() {
    if (!buttonSeat_.has_value()) {
        setBlinds(firstActiveSeat(), smallBlindAmount_, bigBlindAmount_);
        return;
    }
    std::optional<int> nextButton = getNextActivePlayer(*buttonSeat_);
    setBlinds(nextButton.value_or(*buttonSeat_), smallBlindAmount_, bigBlindAmount_);
}

void Table::dealHoleCards() {
    for (Player* player : getActivePlayers()) {
        Card first = deck_.dealCard();
        Card second = deck_.dealCard();
        player->receiveCards(first, second);
    }
}

std::vector<Card> Table::dealCommunityCards(int numCards) {
    std::vector<Card> dealt;
    for (int i = 0; i < numCards; ++i) {
        if (deck_.isEmpty()) {
            break;
        }
        Card card = deck_.dealCard();
        communityCards_.push_back(card);
        dealt.push_back(card);
    }
    return dealt;
}

Street Table::advanceStreet() {
    switch (street_) {
        case Street::PreFlop:
            street_ = Street::Flop;
            dealCommunityCards(3);
            break;
        case Street::Flop:
            street_ = Street::Turn;
            dealCommunityCards(1);
            break;
        case Street::Turn:
            street_ = Street::River;
            dealCommunityCards(1);
            break;
        case Street::River:
            street_ = Street::Showdown;
            break;
        case Street::Showdown:
            street_ = Street::HandComplete;
            break;
        case Street::HandComplete:
            throw std::logic_error("Cannot advance from HandComplete");
    }
    return street_;
}

std::optional<int> Table::getNextActivePlayer(int fromSeat) const {
    for (int i = 1; i < numSeats_; ++i) {
        int seatNum = (fromSeat + i) % numSeats_;
        const Player* player = getPlayer(seatNum);
        if (player && player->canAct()) {
            return seatNum;
        }
    }
    return std::nullopt;
}

std::optional<int> Table::getPreviousActivePlayer(int fromSeat) const {
    for (int i = 1; i < numSeats_; ++i) {
        int seatNum = ((fromSeat - i) % numSeats_ + numSeats_) % numSeats_;
        const Player* player = getPlayer(seatNum);
        if (player && player->canAct()) {
            return seatNum;
        }
    }
    return std::nullopt;
}

bool Table::isButton(int seat) const {
    return seat >= 0 && seat < numSeats_ && markers_[seat].isButton;
}

bool Table::isSmallBlind(int seat) const {
    return seat >= 0 && seat < numSeats_ && markers_[seat].isSmallBlind;
}

bool Table::isBigBlind(int seat) const {
    return seat >= 0 && seat < numSeats_ && markers_[seat].isBigBlind;
}

}  // namespace poker
