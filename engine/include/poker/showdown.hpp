#pragma once

#include <optional>
#include <string>
#include <vector>

#include "poker/card.hpp"
#include "poker/hand_evaluator.hpp"
#include "poker/player.hpp"
#include "poker/pot_manager.hpp"

namespace poker {

/// One player's outcome at the end of a hand. `bestHand` is unset for a
/// player who won by everyone else folding (no showdown happened).
class PlayerResult {
public:
    PlayerResult(int seat, std::string name, std::vector<Card> holeCards, std::optional<Hand> bestHand,
                 int chipsWon)
        : seat_(seat),
          name_(std::move(name)),
          holeCards_(std::move(holeCards)),
          bestHand_(std::move(bestHand)),
          chipsWon_(chipsWon) {}

    int seat() const noexcept { return seat_; }
    const std::string& name() const noexcept { return name_; }
    const std::vector<Card>& holeCards() const noexcept { return holeCards_; }
    const std::optional<Hand>& bestHand() const noexcept { return bestHand_; }
    int chipsWon() const noexcept { return chipsWon_; }

private:
    int seat_;
    std::string name_;
    std::vector<Card> holeCards_;
    std::optional<Hand> bestHand_;
    int chipsWon_;
};

/// The complete outcome of one hand.
class ShowdownResult {
public:
    ShowdownResult(std::vector<PlayerResult> playerResults, bool isShowdown)
        : playerResults_(std::move(playerResults)), isShowdown_(isShowdown) {}

    const std::vector<PlayerResult>& playerResults() const noexcept { return playerResults_; }

    /// True when 2+ players compared cards; false when a single player
    /// won because everyone else folded.
    bool isShowdown() const noexcept { return isShowdown_; }

    /// Players who won chips in this hand.
    std::vector<PlayerResult> winners() const;

    /// Total chips distributed.
    int totalPot() const;

private:
    std::vector<PlayerResult> playerResults_;
    bool isShowdown_;
};

/// Resolves the showdown at the end of a poker hand: evaluates each active
/// player's best hand from their hole cards and the board, awards pots to
/// the strongest eligible hand(s) with tie-breaking, and credits chips to
/// player stacks.
class Showdown {
public:
    /// `activePlayers` must each have exactly 2 hole cards if 2+ players
    /// remain. `communityCards` must have exactly 5 cards in that case (a
    /// fold-win ends before the board is complete, so it's not required
    /// then). `potManager` must already have its pots calculated for this
    /// hand. Winning players' stacks are increased by their winnings as a
    /// side effect. Throws std::invalid_argument if 2+ active players
    /// remain but the board isn't exactly 5 cards.
    static ShowdownResult resolve(const std::vector<Player*>& activePlayers,
                                   const std::vector<Card>& communityCards, PotManager& potManager);
};

}  // namespace poker
