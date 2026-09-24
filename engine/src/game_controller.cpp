#include "poker/game_controller.hpp"

#include <stdexcept>

namespace poker {

GameController::GameController(Table table, int smallBlindAmount, int bigBlindAmount, ProgressionMode mode)
    : table_(std::move(table)),
      smallBlindAmount_(smallBlindAmount),
      bigBlindAmount_(bigBlindAmount),
      mode_(mode) {
    if (smallBlindAmount <= 0 || bigBlindAmount < smallBlindAmount) {
        throw std::invalid_argument("Blinds must satisfy 0 < small blind <= big blind");
    }
}

std::optional<int> GameController::currentSeat() const noexcept {
    if (phase_ != HandPhase::AwaitingAction) {
        return std::nullopt;
    }
    return table_.currentPlayerSeat();
}

void GameController::startHand(const std::vector<Card>& stackedCards) {
    if (phase_ == HandPhase::AwaitingAction || phase_ == HandPhase::PendingAdvance) {
        throw std::logic_error("Cannot start a new hand while one is in progress");
    }
    int playersWithChips = 0;
    for (Player* player : table_.getAllPlayers()) {
        if (player->hasChips()) {
            ++playersWithChips;
        }
    }
    if (playersWithChips < 2) {
        throw std::logic_error("Cannot start a new hand: fewer than 2 players have chips");
    }

    table_.resetForNewHand();
    table_.deck().shuffle();
    table_.deck().putOnTop(stackedCards);

    ++handNumber_;
    round_.reset();
    contributions_.clear();
    potManager_.reset();
    lastResult_.reset();

    table_.setBlindAmounts(smallBlindAmount_, bigBlindAmount_);
    table_.rotateButton();
    table_.dealHoleCards();
    openBettingRound();

    if (mode_ == ProgressionMode::Auto) {
        advance();
    }
}

LegalActions GameController::legalActions() const {
    if (phase_ != HandPhase::AwaitingAction) {
        throw std::logic_error("No player is on the clock");
    }
    int seat = *table_.currentPlayerSeat();
    const Player& player = *table_.getPlayer(seat);
    int stack = player.stack();
    int toCall = round_->getAmountToCall(seat);
    int minRaise = round_->minRaiseAmount();

    // Raising needs someone left who could respond to it.
    bool opponentCanAct = false;
    for (int s = 0; s < table_.numSeats(); ++s) {
        const Player* other = table_.getPlayer(s);
        if (s != seat && other && other->canAct()) {
            opponentCanAct = true;
            break;
        }
    }
    bool mayRaise = opponentCanAct && !round_->isCapped(seat);

    LegalActions legal;
    legal.seat = seat;
    legal.canFold = true;
    legal.canCheck = toCall == 0;
    legal.canCall = toCall > 0 && toCall <= stack;
    legal.callAmount = toCall;

    // Whether opening the betting is a bet or a raise depends on whether
    // anything is wagered this street yet, not on whether this seat owes
    // a call: the big blind's pre-flop option owes nothing but faces a
    // live blind, so it raises.
    if (round_->highestBet() == 0) {
        legal.canBet = mayRaise && stack >= minRaise;
        if (legal.canBet) {
            legal.minBet = minRaise;
            legal.maxBet = stack;
        }
    } else {
        legal.canRaise = mayRaise && stack - toCall >= minRaise;
        if (legal.canRaise) {
            legal.minRaise = minRaise;
            legal.maxRaise = stack - toCall;
        }
    }

    legal.canAllIn = stack > 0 && (stack <= toCall || mayRaise);
    legal.allInAmount = legal.canAllIn ? stack : 0;
    return legal;
}

std::optional<std::string> GameController::validateAction(const Action& action) const {
    if (phase_ != HandPhase::AwaitingAction) {
        return "No player is on the clock.";
    }
    int seat = *table_.currentPlayerSeat();
    if (action.playerSeat() != seat) {
        return "It is seat " + std::to_string(seat) + "'s turn, not seat " +
               std::to_string(action.playerSeat()) + "'s.";
    }

    LegalActions legal = legalActions();
    switch (action.type()) {
        case ActionType::Fold:
            return std::nullopt;
        case ActionType::Check:
            if (!legal.canCheck) {
                return "Cannot check: " + std::to_string(legal.callAmount) + " to call.";
            }
            return std::nullopt;
        case ActionType::Call:
            if (!legal.canCall) {
                return "Cannot call (nothing to call, or the stack is too short - go all-in instead).";
            }
            return std::nullopt;
        case ActionType::Bet:
            if (!legal.canBet) {
                return "Cannot bet right now.";
            }
            if (action.amount() < legal.minBet || action.amount() > legal.maxBet) {
                return "Bet must be between " + std::to_string(legal.minBet) + " and " +
                       std::to_string(legal.maxBet) + ".";
            }
            return std::nullopt;
        case ActionType::Raise:
            if (!legal.canRaise) {
                return "Cannot raise right now.";
            }
            if (action.amount() < legal.minRaise || action.amount() > legal.maxRaise) {
                return "Raise must be between " + std::to_string(legal.minRaise) + " and " +
                       std::to_string(legal.maxRaise) + ".";
            }
            return std::nullopt;
        case ActionType::AllIn:
            if (!legal.canAllIn) {
                return "Cannot go all-in right now (call instead).";
            }
            return std::nullopt;
    }
    return "Unknown action type.";
}

void GameController::submitAction(const Action& action) {
    if (phase_ != HandPhase::AwaitingAction) {
        throw std::logic_error("No player is on the clock");
    }
    if (std::optional<std::string> reason = validateAction(action)) {
        throw std::invalid_argument(*reason);
    }

    round_->processAction(action);
    moveTurnOn();

    if (mode_ == ProgressionMode::Auto) {
        advance();
    }
}

bool GameController::stepOnce() {
    if (phase_ != HandPhase::PendingAdvance) {
        return false;
    }
    collectRoundContributions();

    if (table_.getActivePlayers().size() <= 1 || table_.street() == Street::River) {
        resolveHand();
    } else {
        table_.advanceStreet();
        openBettingRound();
    }
    return true;
}

void GameController::advance() {
    while (stepOnce()) {
    }
}

std::map<int, int> GameController::contributions() const {
    std::map<int, int> totals = contributions_;
    if (round_) {
        for (const auto& [seat, amount] : round_->playerBetAmounts()) {
            totals[seat] += amount;
        }
    }
    return totals;
}

void GameController::openBettingRound() {
    // Pre-flop, action starts left of the big blind (the button/small
    // blind heads-up); after that, left of the button. Seats that can't
    // act (all-in, folded, busted) are skipped.
    std::optional<int> anchor =
        table_.street() == Street::PreFlop ? table_.bigBlindSeat() : table_.buttonSeat();
    int startSeat = table_.getNextActivePlayer(anchor.value_or(0)).value_or(anchor.value_or(0));

    round_.emplace(table_, smallBlindAmount_, bigBlindAmount_, startSeat);
    if (table_.street() == Street::PreFlop) {
        round_->initializeBlinds();
    }

    if (bettingNeeded()) {
        moveTurnOn();
    } else {
        table_.clearCurrentPlayer();
        phase_ = HandPhase::PendingAdvance;
    }
}

bool GameController::bettingNeeded() const {
    // Betting needs two players who can still act - or one who owes chips
    // to an opponent's all-in (e.g. both blinds posted all-in and
    // under-the-gun hasn't called yet).
    std::vector<int> canAct;
    for (int s = 0; s < table_.numSeats(); ++s) {
        const Player* player = table_.getPlayer(s);
        if (player && player->canAct()) {
            canAct.push_back(s);
        }
    }
    if (canAct.size() >= 2) {
        return true;
    }
    return canAct.size() == 1 && round_->getAmountToCall(canAct[0]) > 0;
}

void GameController::moveTurnOn() {
    std::optional<int> next;
    if (table_.getActivePlayers().size() > 1) {
        next = round_->getNextToAct();
    }
    if (next.has_value()) {
        table_.setCurrentPlayer(*next);
        phase_ = HandPhase::AwaitingAction;
    } else {
        table_.clearCurrentPlayer();
        phase_ = HandPhase::PendingAdvance;
    }
}

void GameController::collectRoundContributions() {
    if (!round_) {
        return;
    }
    for (const auto& [seat, amount] : round_->playerBetAmounts()) {
        contributions_[seat] += amount;
    }
    round_.reset();
}

void GameController::resolveHand() {
    std::vector<Player*> inHand = table_.getActivePlayers();
    potManager_.calculatePots(contributions_);
    if (inHand.size() > 1) {
        table_.advanceStreet();  // River -> Showdown
    }
    lastResult_ = Showdown::resolve(inHand, table_.communityCards(), potManager_);
    table_.finishHand();
    phase_ = HandPhase::HandComplete;
}

}  // namespace poker
