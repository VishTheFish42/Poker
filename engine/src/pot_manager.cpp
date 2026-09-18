#include "poker/pot_manager.hpp"

#include <algorithm>

namespace poker {

int PotManager::getTotal() const {
    int total = 0;
    for (const Pot& pot : pots_) {
        total += pot.amount;
    }
    return total;
}

void PotManager::calculatePots(const std::map<int, int>& contributions) {
    pots_.clear();
    if (contributions.empty()) {
        return;
    }

    std::map<int, int> remaining = contributions;
    while (!remaining.empty()) {
        int cap = remaining.begin()->second;
        for (const auto& [seat, amount] : remaining) {
            cap = std::min(cap, amount);
        }

        Pot pot{cap * static_cast<int>(remaining.size()), {}};
        for (const auto& [seat, amount] : remaining) {
            pot.eligibleSeats.push_back(seat);
        }
        pots_.push_back(std::move(pot));

        std::map<int, int> next;
        for (const auto& [seat, amount] : remaining) {
            int rest = amount - cap;
            if (rest > 0) {
                next[seat] = rest;
            }
        }
        remaining = std::move(next);
    }
}

std::map<int, int> PotManager::awardPots(const std::map<int, Hand>& hands) const {
    std::map<int, int> winnings;
    for (const auto& [seat, hand] : hands) {
        winnings[seat] = 0;
    }

    for (const Pot& pot : pots_) {
        std::vector<int> contenders;
        for (int seat : pot.eligibleSeats) {
            if (hands.count(seat) > 0) {
                contenders.push_back(seat);
            }
        }
        if (contenders.empty()) {
            continue;
        }
        if (contenders.size() == 1) {
            winnings[contenders[0]] += pot.amount;
            continue;
        }

        const Hand* best = &hands.at(contenders[0]);
        for (int seat : contenders) {
            const Hand& hand = hands.at(seat);
            if (hand > *best) {
                best = &hand;
            }
        }

        std::vector<int> winners;
        for (int seat : contenders) {
            if (hands.at(seat) == *best) {
                winners.push_back(seat);
            }
        }
        std::sort(winners.begin(), winners.end());

        int share = pot.amount / static_cast<int>(winners.size());
        int remainder = pot.amount % static_cast<int>(winners.size());
        for (int seat : winners) {
            winnings[seat] += share;
        }
        for (int i = 0; i < remainder; ++i) {
            winnings[winners[i]] += 1;
        }
    }

    return winnings;
}

}  // namespace poker
