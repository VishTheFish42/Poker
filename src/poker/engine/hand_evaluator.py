"""Hand evaluation and ranking for Texas Hold'em poker."""

from enum import Enum
from typing import List, Tuple
from itertools import combinations

from .card import Card, CardRank, CardSuit


class HandType(Enum):
    """Enumeration of poker hand types ranked from highest to lowest."""
    ROYAL_FLUSH = 10
    STRAIGHT_FLUSH = 9
    FOUR_OF_A_KIND = 8
    FULL_HOUSE = 7
    FLUSH = 6
    STRAIGHT = 5
    THREE_OF_A_KIND = 4
    TWO_PAIR = 3
    ONE_PAIR = 2
    HIGH_CARD = 1

    def __lt__(self, other: "HandType") -> bool:
        """Compare hand types by rank."""
        if not isinstance(other, HandType):
            return NotImplemented
        return self.value < other.value

    def __le__(self, other: "HandType") -> bool:
        """Compare hand types by rank (less than or equal)."""
        if not isinstance(other, HandType):
            return NotImplemented
        return self.value <= other.value

    def __gt__(self, other: "HandType") -> bool:
        """Compare hand types by rank (greater than)."""
        if not isinstance(other, HandType):
            return NotImplemented
        return self.value > other.value

    def __ge__(self, other: "HandType") -> bool:
        """Compare hand types by rank (greater than or equal)."""
        if not isinstance(other, HandType):
            return NotImplemented
        return self.value >= other.value


class Hand:
    """Represents an evaluated 5-card poker hand."""

    def __init__(
        self,
        hand_type: HandType,
        rank_value: int,
        kickers: List[int],
        cards: List[Card],
    ) -> None:
        """Initialize a Hand with its type, rank, and kicker values.

        Args:
            hand_type: The type of hand (e.g., ONE_PAIR, STRAIGHT)
            rank_value: Numeric rank for the primary component (e.g., pair rank)
            kickers: List of numeric ranks for tie-breaking, in descending order
            cards: The 5 cards that make up this hand
        """
        self.hand_type = hand_type
        self.rank_value = rank_value
        self.kickers = kickers
        self.cards = cards

    def __repr__(self) -> str:
        """Return a string representation of the hand."""
        return f"{self.hand_type.name} ({', '.join(str(card) for card in self.cards)})"

    def __lt__(self, other: "Hand") -> bool:
        """Compare two hands for ranking (self < other means self is weaker)."""
        if not isinstance(other, Hand):
            return NotImplemented

        # Compare hand types first
        if self.hand_type != other.hand_type:
            return self.hand_type < other.hand_type

        # Same hand type, compare rank values
        if self.rank_value != other.rank_value:
            return self.rank_value < other.rank_value

        # Compare kickers for tie-breaking
        for self_kicker, other_kicker in zip(self.kickers, other.kickers):
            if self_kicker != other_kicker:
                return self_kicker < other_kicker

        # Hands are equal
        return False

    def __le__(self, other: "Hand") -> bool:
        """Compare hands (less than or equal)."""
        if not isinstance(other, Hand):
            return NotImplemented
        return self < other or self == other

    def __gt__(self, other: "Hand") -> bool:
        """Compare hands (greater than)."""
        if not isinstance(other, Hand):
            return NotImplemented
        return other < self

    def __ge__(self, other: "Hand") -> bool:
        """Compare hands (greater than or equal)."""
        if not isinstance(other, Hand):
            return NotImplemented
        return other <= self

    def __eq__(self, other: object) -> bool:
        """Check if two hands are equal."""
        if not isinstance(other, Hand):
            return NotImplemented
        return (
            self.hand_type == other.hand_type
            and self.rank_value == other.rank_value
            and self.kickers == other.kickers
        )


class HandEvaluator:
    """Evaluates and ranks poker hands."""

    @staticmethod
    def evaluate_hand(cards: List[Card]) -> Hand:
        """Evaluate a 5-card poker hand and return its type and rank.

        Args:
            cards: List of exactly 5 cards to evaluate.

        Returns:
            A Hand object representing the evaluated hand.

        Raises:
            ValueError: If not exactly 5 cards are provided.
        """
        if len(cards) != 5:
            raise ValueError("Must evaluate exactly 5 cards.")

        # Check hand types in order from strongest to weakest
        if HandEvaluator._is_straight_flush(cards):
            return HandEvaluator._evaluate_straight_flush(cards)
        elif HandEvaluator._is_four_of_a_kind(cards):
            return HandEvaluator._evaluate_four_of_a_kind(cards)
        elif HandEvaluator._is_full_house(cards):
            return HandEvaluator._evaluate_full_house(cards)
        elif HandEvaluator._is_flush(cards):
            return HandEvaluator._evaluate_flush(cards)
        elif HandEvaluator._is_straight(cards):
            return HandEvaluator._evaluate_straight(cards)
        elif HandEvaluator._is_three_of_a_kind(cards):
            return HandEvaluator._evaluate_three_of_a_kind(cards)
        elif HandEvaluator._is_two_pair(cards):
            return HandEvaluator._evaluate_two_pair(cards)
        elif HandEvaluator._is_one_pair(cards):
            return HandEvaluator._evaluate_one_pair(cards)
        else:
            return HandEvaluator._evaluate_high_card(cards)

    @staticmethod
    def best_hand_from_seven(cards: List[Card]) -> Hand:
        """Find the best 5-card hand from 7 cards (Texas Hold'em).

        Args:
            cards: List of exactly 7 cards (2 hole + 5 community).

        Returns:
            The best Hand that can be made from the 7 cards.

        Raises:
            ValueError: If not exactly 7 cards are provided.
        """
        if len(cards) != 7:
            raise ValueError("Must provide exactly 7 cards for best hand selection.")

        best_hand = None
        for combo in combinations(cards, 5):
            hand = HandEvaluator.evaluate_hand(list(combo))
            if best_hand is None or hand > best_hand:
                best_hand = hand

        return best_hand

    @staticmethod
    def compare_hands(hands: List[Tuple[int, Hand]]) -> List[int]:
        """Compare multiple hands and return seat indices ranked from best to worst.

        Args:
            hands: List of (seat_index, Hand) tuples.

        Returns:
            List of seat indices ordered from strongest to weakest hand.
        """
        # Sort by hand strength (descending), keeping track of original seat indices
        sorted_hands = sorted(hands, key=lambda x: x[1], reverse=True)
        return [seat for seat, _ in sorted_hands]

    # Private helper methods for hand detection

    @staticmethod
    def _is_flush(cards: List[Card]) -> bool:
        """Check if 5 cards form a flush."""
        suits = [card.suit for card in cards]
        return len(set(suits)) == 1

    @staticmethod
    def _is_straight(cards: List[Card]) -> bool:
        """Check if 5 cards form a straight."""
        ranks = sorted([card.rank.numeric_value for card in cards])
        # Check for normal straight
        if ranks[-1] - ranks[0] == 4 and len(set(ranks)) == 5:
            return True
        # Check for A-2-3-4-5 (wheel/bicycle)
        if ranks == [2, 3, 4, 5, 14]:
            return True
        return False

    @staticmethod
    def _get_straight_high(cards: List[Card]) -> int:
        """Get the high card rank of a straight."""
        ranks = sorted([card.rank.numeric_value for card in cards])
        # Wheel (A-2-3-4-5) has high card of 5, not 14
        if ranks == [2, 3, 4, 5, 14]:
            return 5
        return ranks[-1]

    @staticmethod
    def _is_straight_flush(cards: List[Card]) -> bool:
        """Check if 5 cards form a straight flush."""
        return HandEvaluator._is_flush(cards) and HandEvaluator._is_straight(cards)

    @staticmethod
    def _is_four_of_a_kind(cards: List[Card]) -> bool:
        """Check if 5 cards contain four of a kind."""
        ranks = [card.rank.numeric_value for card in cards]
        return max([ranks.count(r) for r in ranks]) == 4

    @staticmethod
    def _is_full_house(cards: List[Card]) -> bool:
        """Check if 5 cards form a full house (three of a kind + pair)."""
        ranks = [card.rank.numeric_value for card in cards]
        counts = sorted([ranks.count(r) for r in set(ranks)])
        return counts == [2, 3]

    @staticmethod
    def _is_three_of_a_kind(cards: List[Card]) -> bool:
        """Check if 5 cards contain three of a kind."""
        ranks = [card.rank.numeric_value for card in cards]
        return max([ranks.count(r) for r in ranks]) == 3

    @staticmethod
    def _is_two_pair(cards: List[Card]) -> bool:
        """Check if 5 cards contain two pair."""
        ranks = [card.rank.numeric_value for card in cards]
        counts = sorted([ranks.count(r) for r in set(ranks)])
        return counts == [1, 2, 2]

    @staticmethod
    def _is_one_pair(cards: List[Card]) -> bool:
        """Check if 5 cards contain one pair."""
        ranks = [card.rank.numeric_value for card in cards]
        return max([ranks.count(r) for r in ranks]) == 2

    # Private evaluation methods returning Hand objects

    @staticmethod
    def _evaluate_straight_flush(cards: List[Card]) -> Hand:
        """Evaluate a straight flush."""
        high = HandEvaluator._get_straight_high(cards)
        # Royal flush is A-K-Q-J-10
        if high == 14:
            return Hand(HandType.ROYAL_FLUSH, 14, [], cards)
        return Hand(HandType.STRAIGHT_FLUSH, high, [], cards)

    @staticmethod
    def _evaluate_four_of_a_kind(cards: List[Card]) -> Hand:
        """Evaluate four of a kind."""
        ranks = [card.rank.numeric_value for card in cards]
        quad_rank = [r for r in set(ranks) if ranks.count(r) == 4][0]
        kicker = [r for r in set(ranks) if ranks.count(r) == 1][0]
        return Hand(HandType.FOUR_OF_A_KIND, quad_rank, [kicker], cards)

    @staticmethod
    def _evaluate_full_house(cards: List[Card]) -> Hand:
        """Evaluate a full house."""
        ranks = [card.rank.numeric_value for card in cards]
        trips_rank = [r for r in set(ranks) if ranks.count(r) == 3][0]
        pair_rank = [r for r in set(ranks) if ranks.count(r) == 2][0]
        return Hand(HandType.FULL_HOUSE, trips_rank, [pair_rank], cards)

    @staticmethod
    def _evaluate_flush(cards: List[Card]) -> Hand:
        """Evaluate a flush."""
        ranks = sorted([card.rank.numeric_value for card in cards], reverse=True)
        return Hand(HandType.FLUSH, ranks[0], ranks[1:], cards)

    @staticmethod
    def _evaluate_straight(cards: List[Card]) -> Hand:
        """Evaluate a straight."""
        high = HandEvaluator._get_straight_high(cards)
        return Hand(HandType.STRAIGHT, high, [], cards)

    @staticmethod
    def _evaluate_three_of_a_kind(cards: List[Card]) -> Hand:
        """Evaluate three of a kind."""
        ranks = [card.rank.numeric_value for card in cards]
        trips_rank = [r for r in set(ranks) if ranks.count(r) == 3][0]
        kickers = sorted([r for r in set(ranks) if ranks.count(r) == 1], reverse=True)
        return Hand(HandType.THREE_OF_A_KIND, trips_rank, kickers, cards)

    @staticmethod
    def _evaluate_two_pair(cards: List[Card]) -> Hand:
        """Evaluate two pair."""
        ranks = [card.rank.numeric_value for card in cards]
        pairs = sorted([r for r in set(ranks) if ranks.count(r) == 2], reverse=True)
        kicker = [r for r in set(ranks) if ranks.count(r) == 1][0]
        return Hand(HandType.TWO_PAIR, pairs[0], [pairs[1], kicker], cards)

    @staticmethod
    def _evaluate_one_pair(cards: List[Card]) -> Hand:
        """Evaluate one pair."""
        ranks = [card.rank.numeric_value for card in cards]
        pair_rank = [r for r in set(ranks) if ranks.count(r) == 2][0]
        kickers = sorted([r for r in set(ranks) if ranks.count(r) == 1], reverse=True)
        return Hand(HandType.ONE_PAIR, pair_rank, kickers, cards)

    @staticmethod
    def _evaluate_high_card(cards: List[Card]) -> Hand:
        """Evaluate high card."""
        ranks = sorted([card.rank.numeric_value for card in cards], reverse=True)
        return Hand(HandType.HIGH_CARD, ranks[0], ranks[1:], cards)
