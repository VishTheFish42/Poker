#include "poker/showdown.hpp"

#include <map>
#include <stdexcept>

namespace poker {

std::vector<PlayerResult> ShowdownResult::winners() const {
    std::vector<PlayerResult> result;
    for (const PlayerResult& r : playerResults_) {
        if (r.chipsWon() > 0) {
            result.push_back(r);
        }
    }
    return result;
}

int ShowdownResult::totalPot() const {
    int total = 0;
    for (const PlayerResult& r : playerResults_) {
        total += r.chipsWon();
    }
    return total;
}

ShowdownResult Showdown::resolve(const std::vector<Player*>& activePlayers,
                                  const std::vector<Card>& communityCards, PotManager& potManager) {
    if (activePlayers.empty()) {
        return ShowdownResult({}, false);
    }

    bool isShowdown = activePlayers.size() > 1;
    std::map<int, Hand> hands;
    std::map<int, int> winnings;

    if (isShowdown) {
        if (communityCards.size() != 5) {
            throw std::invalid_argument("Showdown requires exactly 5 community cards");
        }
        for (Player* player : activePlayers) {
            std::vector<Card> seven = player->holeCards();
            seven.insert(seven.end(), communityCards.begin(), communityCards.end());
            hands.emplace(player->seat(), HandEvaluator::bestHandFromSeven(seven));
        }
        winnings = potManager.awardPots(hands);
    } else {
        winnings[activePlayers.front()->seat()] = potManager.getTotal();
    }

    for (Player* player : activePlayers) {
        auto it = winnings.find(player->seat());
        int won = it != winnings.end() ? it->second : 0;
        if (won > 0) {
            player->addChips(won);
        }
    }

    std::vector<PlayerResult> results;
    results.reserve(activePlayers.size());
    for (Player* player : activePlayers) {
        auto handIt = hands.find(player->seat());
        std::optional<Hand> bestHand =
            handIt != hands.end() ? std::optional<Hand>(handIt->second) : std::nullopt;
        auto winIt = winnings.find(player->seat());
        int won = winIt != winnings.end() ? winIt->second : 0;
        results.emplace_back(player->seat(), player->name(), player->holeCards(), std::move(bestHand), won);
    }

    return ShowdownResult(std::move(results), isShowdown);
}

}  // namespace poker
