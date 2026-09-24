#pragma once

#include <cstdint>
#include <optional>
#include <vector>

#include "poker/card.hpp"
#include "poker/deck.hpp"
#include "poker/player.hpp"

namespace poker {

/// The street of the current hand.
enum class Street : uint8_t {
    PreFlop,
    Flop,
    Turn,
    River,
    Showdown,
    HandComplete,
};

/// 0-4 for PreFlop..Showdown, -1 for HandComplete (no street number).
int streetNumber(Street street) noexcept;

/// Seats, deck, community cards, pot, and blind/button state for one
/// table. Owns the `Player`s seated at it.
class Table {
public:
    static constexpr int kMaxPlayers = 10;

    /// Throws std::invalid_argument unless 2 <= numSeats <= kMaxPlayers.
    explicit Table(int numSeats);

    int numSeats() const noexcept { return numSeats_; }

    /// Throws std::invalid_argument if the player's seat is out of range
    /// or already occupied.
    void addPlayer(Player player);

    /// Removes and returns the player at `seatNumber`, or nullopt if the
    /// seat was invalid or already empty.
    std::optional<Player> removePlayer(int seatNumber);

    Player* getPlayer(int seatNumber) noexcept;
    const Player* getPlayer(int seatNumber) const noexcept;

    /// Seated players who are still in the hand (Active or AllIn).
    std::vector<Player*> getActivePlayers();

    /// All seated players, regardless of status.
    std::vector<Player*> getAllPlayers();

    /// Resets every seated player and the table's per-hand state (deck,
    /// board, street, pot) for a new hand. Does not move the button.
    void resetForNewHand();

    /// Sets the button to `buttonSeat` and recomputes small/big blind
    /// seats by walking forward through active players only (so empty or
    /// busted seats are skipped). Heads-up (exactly 2 active players) is a
    /// special case: the button posts the small blind.
    void setBlinds(int buttonSeat, int smallBlindAmount, int bigBlindAmount);

    /// Sets the blind amounts `rotateButton()` posts with, without moving
    /// the button or recomputing blind seats.
    void setBlindAmounts(int smallBlindAmount, int bigBlindAmount) noexcept {
        smallBlindAmount_ = smallBlindAmount;
        bigBlindAmount_ = bigBlindAmount;
    }

    /// Advances the button to the next active seat (or picks the first
    /// active seat if no button has been set yet) and recomputes blinds,
    /// keeping the current blind amounts.
    void rotateButton();

    /// Deals 2 hole cards to every active player.
    void dealHoleCards();

    /// Deals up to `numCards` from the deck onto the board (fewer if the
    /// deck runs out). Returns the cards dealt.
    std::vector<Card> dealCommunityCards(int numCards);

    /// Advances to the next street, burning one card and then dealing the
    /// flop/turn/river as appropriate. Throws std::logic_error if already
    /// HandComplete.
    Street advanceStreet();

    /// Jumps straight to HandComplete (e.g. everyone else folded before
    /// the river) without dealing any more board cards, and clears the
    /// current player.
    void finishHand() noexcept {
        street_ = Street::HandComplete;
        currentPlayerSeat_.reset();
    }

    void setCurrentPlayer(int seatNumber) noexcept { currentPlayerSeat_ = seatNumber; }
    void clearCurrentPlayer() noexcept { currentPlayerSeat_.reset(); }
    std::optional<int> currentPlayerSeat() const noexcept { return currentPlayerSeat_; }

    /// Next/previous seat (wrapping) after/before `fromSeat` occupied by a
    /// player who canAct(), or nullopt if there isn't one.
    std::optional<int> getNextActivePlayer(int fromSeat) const;
    std::optional<int> getPreviousActivePlayer(int fromSeat) const;

    void setPot(int amount) noexcept { totalPot_ = amount < 0 ? 0 : amount; }
    void addToPot(int amount) noexcept { totalPot_ += amount < 0 ? 0 : amount; }
    int totalPot() const noexcept { return totalPot_; }

    Deck& deck() noexcept { return deck_; }
    const std::vector<Card>& communityCards() const noexcept { return communityCards_; }
    /// Cards burned (dealt face down, out of play) this hand, one before
    /// each of the flop, turn, and river.
    const std::vector<Card>& burnedCards() const noexcept { return burnedCards_; }
    Street street() const noexcept { return street_; }

    std::optional<int> buttonSeat() const noexcept { return buttonSeat_; }
    std::optional<int> smallBlindSeat() const noexcept { return smallBlindSeat_; }
    std::optional<int> bigBlindSeat() const noexcept { return bigBlindSeat_; }
    int smallBlindAmount() const noexcept { return smallBlindAmount_; }
    int bigBlindAmount() const noexcept { return bigBlindAmount_; }

    bool isButton(int seat) const;
    bool isSmallBlind(int seat) const;
    bool isBigBlind(int seat) const;

private:
    struct SeatMarkers {
        bool isButton = false;
        bool isSmallBlind = false;
        bool isBigBlind = false;
    };

    /// First occupied seat with a player who canAct(), for the very first
    /// hand at the table before any button has been set. 0 if none.
    int firstActiveSeat() const;

    /// Moves the top card of the deck to the burn pile (no-op if empty).
    void burnCard();

    int numSeats_;
    std::vector<std::optional<Player>> players_;
    std::vector<SeatMarkers> markers_;
    Deck deck_;
    std::vector<Card> communityCards_;
    std::vector<Card> burnedCards_;
    Street street_ = Street::PreFlop;
    std::optional<int> currentPlayerSeat_;
    int totalPot_ = 0;
    std::optional<int> buttonSeat_;
    std::optional<int> smallBlindSeat_;
    std::optional<int> bigBlindSeat_;
    int smallBlindAmount_ = 1;
    int bigBlindAmount_ = 2;
};

}  // namespace poker
