"""Card and Deck abstractions for the poker game engine."""

from enum import Enum
from typing import List
import random


class CardSuit(Enum):
    """Enumeration of card suits."""
    HEARTS = "♥"
    DIAMONDS = "♦"
    CLUBS = "♣"
    SPADES = "♠"

    def __str__(self) -> str:
        return self.value


class CardRank(Enum):
    """Enumeration of card ranks with numeric values for comparison."""
    TWO = (2, "2")
    THREE = (3, "3")
    FOUR = (4, "4")
    FIVE = (5, "5")
    SIX = (6, "6")
    SEVEN = (7, "7")
    EIGHT = (8, "8")
    NINE = (9, "9")
    TEN = (10, "10")
    JACK = (11, "J")
    QUEEN = (12, "Q")
    KING = (13, "K")
    ACE = (14, "A")

    def __init__(self, numeric_value: int, display: str) -> None:
        self.numeric_value = numeric_value
        self.display = display

    def __str__(self) -> str:
        return self.display


class Card:
    """Represents a single playing card with suit and rank."""

    def __init__(self, suit: CardSuit, rank: CardRank) -> None:
        """Initialize a card with a suit and rank.

        Args:
            suit: The suit of the card (HEARTS, DIAMONDS, CLUBS, SPADES)
            rank: The rank of the card (2-10, J, Q, K, A)
        """
        self.suit = suit
        self.rank = rank

    def __repr__(self) -> str:
        """Return a string representation of the card."""
        return f"{self.rank}{self.suit}"

    def __str__(self) -> str:
        """Return a readable string representation of the card."""
        return f"{self.rank} of {self.suit.name}"

    def __hash__(self) -> int:
        """Return hash of the card for use in sets and dicts."""
        return hash((self.suit, self.rank))

    def __eq__(self, other: object) -> bool:
        """Check equality between two cards."""
        if not isinstance(other, Card):
            return NotImplemented
        return self.suit == other.suit and self.rank == other.rank

    def __lt__(self, other: "Card") -> bool:
        """Compare cards by rank (for sorting)."""
        if not isinstance(other, Card):
            return NotImplemented
        return self.rank.numeric_value < other.rank.numeric_value

    def __le__(self, other: "Card") -> bool:
        """Compare cards by rank (less than or equal)."""
        if not isinstance(other, Card):
            return NotImplemented
        return self.rank.numeric_value <= other.rank.numeric_value

    def __gt__(self, other: "Card") -> bool:
        """Compare cards by rank (greater than)."""
        if not isinstance(other, Card):
            return NotImplemented
        return self.rank.numeric_value > other.rank.numeric_value

    def __ge__(self, other: "Card") -> bool:
        """Compare cards by rank (greater than or equal)."""
        if not isinstance(other, Card):
            return NotImplemented
        return self.rank.numeric_value >= other.rank.numeric_value


class Deck:
    """Represents a standard 52-card poker deck."""

    FULL_DECK_SIZE = 52

    def __init__(self) -> None:
        """Initialize a full, unshuffled deck of 52 cards."""
        self.cards: List[Card] = []
        self.reset()

    def reset(self) -> None:
        """Reset the deck to a full, unshuffled state."""
        self.cards = [
            Card(suit, rank)
            for suit in CardSuit
            for rank in CardRank
        ]

    def shuffle(self) -> None:
        """Shuffle the deck randomly."""
        random.shuffle(self.cards)

    def deal_card(self) -> Card:
        """Deal and remove the top card from the deck.

        Returns:
            The next card from the deck.

        Raises:
            ValueError: If no cards remain in the deck.
        """
        if not self.cards:
            raise ValueError("Cannot deal from an empty deck.")
        return self.cards.pop()

    def peek_card(self) -> Card:
        """Peek at the top card without removing it.

        Returns:
            The next card that would be dealt.

        Raises:
            ValueError: If no cards remain in the deck.
        """
        if not self.cards:
            raise ValueError("Cannot peek at an empty deck.")
        return self.cards[-1]

    def remaining(self) -> int:
        """Return the number of cards remaining in the deck.

        Returns:
            Number of cards left to deal.
        """
        return len(self.cards)

    def is_empty(self) -> bool:
        """Check if the deck is empty.

        Returns:
            True if no cards remain, False otherwise.
        """
        return len(self.cards) == 0

    def __repr__(self) -> str:
        """Return a string representation of the deck state."""
        return f"Deck({self.remaining()} cards)"

    def __len__(self) -> int:
        """Return the number of cards in the deck."""
        return len(self.cards)

    def __iter__(self):
        """Allow iteration over cards in the deck."""
        return iter(self.cards)
