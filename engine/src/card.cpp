#include "poker/card.hpp"

namespace poker {

std::string suitSymbol(Suit suit) {
    switch (suit) {
        case Suit::Hearts:
            return "♥";
        case Suit::Diamonds:
            return "♦";
        case Suit::Clubs:
            return "♣";
        case Suit::Spades:
            return "♠";
    }
    return "?";
}

std::string rankDisplay(Rank rank) {
    switch (rank) {
        case Rank::Two:
            return "2";
        case Rank::Three:
            return "3";
        case Rank::Four:
            return "4";
        case Rank::Five:
            return "5";
        case Rank::Six:
            return "6";
        case Rank::Seven:
            return "7";
        case Rank::Eight:
            return "8";
        case Rank::Nine:
            return "9";
        case Rank::Ten:
            return "10";
        case Rank::Jack:
            return "J";
        case Rank::Queen:
            return "Q";
        case Rank::King:
            return "K";
        case Rank::Ace:
            return "A";
    }
    return "?";
}

std::string Card::toString() const {
    return rankDisplay(rank_) + suitSymbol(suit_);
}

}  // namespace poker
