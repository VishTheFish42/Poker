"""Unit tests for hand evaluator."""

import pytest
from src.poker.engine.card import Card, CardRank, CardSuit
from src.poker.engine.hand_evaluator import Hand, HandEvaluator, HandType


class TestHandEvaluation:
    """Test cases for hand evaluation."""

    def test_high_card(self):
        """Test evaluation of high card."""
        cards = [
            Card(CardSuit.HEARTS, CardRank.ACE),
            Card(CardSuit.DIAMONDS, CardRank.KING),
            Card(CardSuit.CLUBS, CardRank.QUEEN),
            Card(CardSuit.SPADES, CardRank.JACK),
            Card(CardSuit.HEARTS, CardRank.NINE),
        ]
        hand = HandEvaluator.evaluate_hand(cards)
        assert hand.hand_type == HandType.HIGH_CARD
        assert hand.rank_value == 14  # Ace

    def test_one_pair(self):
        """Test evaluation of one pair."""
        cards = [
            Card(CardSuit.HEARTS, CardRank.ACE),
            Card(CardSuit.DIAMONDS, CardRank.ACE),
            Card(CardSuit.CLUBS, CardRank.KING),
            Card(CardSuit.SPADES, CardRank.QUEEN),
            Card(CardSuit.HEARTS, CardRank.JACK),
        ]
        hand = HandEvaluator.evaluate_hand(cards)
        assert hand.hand_type == HandType.ONE_PAIR
        assert hand.rank_value == 14  # Pair of Aces

    def test_two_pair(self):
        """Test evaluation of two pair."""
        cards = [
            Card(CardSuit.HEARTS, CardRank.ACE),
            Card(CardSuit.DIAMONDS, CardRank.ACE),
            Card(CardSuit.CLUBS, CardRank.KING),
            Card(CardSuit.SPADES, CardRank.KING),
            Card(CardSuit.HEARTS, CardRank.QUEEN),
        ]
        hand = HandEvaluator.evaluate_hand(cards)
        assert hand.hand_type == HandType.TWO_PAIR
        assert hand.rank_value == 14  # Higher pair is Aces

    def test_three_of_a_kind(self):
        """Test evaluation of three of a kind."""
        cards = [
            Card(CardSuit.HEARTS, CardRank.ACE),
            Card(CardSuit.DIAMONDS, CardRank.ACE),
            Card(CardSuit.CLUBS, CardRank.ACE),
            Card(CardSuit.SPADES, CardRank.KING),
            Card(CardSuit.HEARTS, CardRank.QUEEN),
        ]
        hand = HandEvaluator.evaluate_hand(cards)
        assert hand.hand_type == HandType.THREE_OF_A_KIND
        assert hand.rank_value == 14  # Three Aces

    def test_straight(self):
        """Test evaluation of a straight."""
        cards = [
            Card(CardSuit.HEARTS, CardRank.FIVE),
            Card(CardSuit.DIAMONDS, CardRank.FOUR),
            Card(CardSuit.CLUBS, CardRank.THREE),
            Card(CardSuit.SPADES, CardRank.TWO),
            Card(CardSuit.HEARTS, CardRank.ACE),
        ]
        hand = HandEvaluator.evaluate_hand(cards)
        assert hand.hand_type == HandType.STRAIGHT
        assert hand.rank_value == 5  # Wheel (A-2-3-4-5)

    def test_straight_normal(self):
        """Test evaluation of a normal straight."""
        cards = [
            Card(CardSuit.HEARTS, CardRank.KING),
            Card(CardSuit.DIAMONDS, CardRank.QUEEN),
            Card(CardSuit.CLUBS, CardRank.JACK),
            Card(CardSuit.SPADES, CardRank.TEN),
            Card(CardSuit.HEARTS, CardRank.NINE),
        ]
        hand = HandEvaluator.evaluate_hand(cards)
        assert hand.hand_type == HandType.STRAIGHT
        assert hand.rank_value == 13  # King-high straight

    def test_flush(self):
        """Test evaluation of a flush."""
        cards = [
            Card(CardSuit.HEARTS, CardRank.ACE),
            Card(CardSuit.HEARTS, CardRank.KING),
            Card(CardSuit.HEARTS, CardRank.QUEEN),
            Card(CardSuit.HEARTS, CardRank.JACK),
            Card(CardSuit.HEARTS, CardRank.NINE),
        ]
        hand = HandEvaluator.evaluate_hand(cards)
        assert hand.hand_type == HandType.FLUSH

    def test_full_house(self):
        """Test evaluation of a full house."""
        cards = [
            Card(CardSuit.HEARTS, CardRank.ACE),
            Card(CardSuit.DIAMONDS, CardRank.ACE),
            Card(CardSuit.CLUBS, CardRank.ACE),
            Card(CardSuit.SPADES, CardRank.KING),
            Card(CardSuit.HEARTS, CardRank.KING),
        ]
        hand = HandEvaluator.evaluate_hand(cards)
        assert hand.hand_type == HandType.FULL_HOUSE
        assert hand.rank_value == 14  # Three Aces

    def test_four_of_a_kind(self):
        """Test evaluation of four of a kind."""
        cards = [
            Card(CardSuit.HEARTS, CardRank.ACE),
            Card(CardSuit.DIAMONDS, CardRank.ACE),
            Card(CardSuit.CLUBS, CardRank.ACE),
            Card(CardSuit.SPADES, CardRank.ACE),
            Card(CardSuit.HEARTS, CardRank.KING),
        ]
        hand = HandEvaluator.evaluate_hand(cards)
        assert hand.hand_type == HandType.FOUR_OF_A_KIND
        assert hand.rank_value == 14  # Four Aces

    def test_straight_flush(self):
        """Test evaluation of a straight flush."""
        cards = [
            Card(CardSuit.HEARTS, CardRank.KING),
            Card(CardSuit.HEARTS, CardRank.QUEEN),
            Card(CardSuit.HEARTS, CardRank.JACK),
            Card(CardSuit.HEARTS, CardRank.TEN),
            Card(CardSuit.HEARTS, CardRank.NINE),
        ]
        hand = HandEvaluator.evaluate_hand(cards)
        assert hand.hand_type == HandType.STRAIGHT_FLUSH

    def test_royal_flush(self):
        """Test evaluation of a royal flush."""
        cards = [
            Card(CardSuit.HEARTS, CardRank.ACE),
            Card(CardSuit.HEARTS, CardRank.KING),
            Card(CardSuit.HEARTS, CardRank.QUEEN),
            Card(CardSuit.HEARTS, CardRank.JACK),
            Card(CardSuit.HEARTS, CardRank.TEN),
        ]
        hand = HandEvaluator.evaluate_hand(cards)
        assert hand.hand_type == HandType.ROYAL_FLUSH


class TestHandComparison:
    """Test cases for hand comparison."""

    def test_pair_beats_high_card(self):
        """Test that a pair beats high card."""
        pair = Hand(HandType.ONE_PAIR, 14, [13, 12, 11], [])
        high_card = Hand(HandType.HIGH_CARD, 14, [13, 12, 11, 10], [])
        assert pair > high_card

    def test_two_pair_beats_one_pair(self):
        """Test that two pair beats one pair."""
        two_pair = Hand(HandType.TWO_PAIR, 14, [13, 11], [])
        one_pair = Hand(HandType.ONE_PAIR, 14, [13, 12, 11], [])
        assert two_pair > one_pair

    def test_higher_kicker_wins(self):
        """Test that higher kicker wins with same hand type."""
        hand1 = Hand(HandType.ONE_PAIR, 14, [13, 12], [])
        hand2 = Hand(HandType.ONE_PAIR, 14, [13, 11], [])
        assert hand1 > hand2

    def test_hands_equal(self):
        """Test equality of hands."""
        hand1 = Hand(HandType.ONE_PAIR, 14, [13, 12], [])
        hand2 = Hand(HandType.ONE_PAIR, 14, [13, 12], [])
        assert hand1 == hand2


class TestBestHandFromSeven:
    """Test cases for selecting best hand from 7 cards."""

    def test_best_hand_from_seven(self):
        """Test selecting best 5-card hand from 7 cards."""
        # Two pair from hole cards, potential flush from community
        cards = [
            Card(CardSuit.HEARTS, CardRank.ACE),
            Card(CardSuit.HEARTS, CardRank.KING),
            Card(CardSuit.HEARTS, CardRank.QUEEN),
            Card(CardSuit.HEARTS, CardRank.JACK),
            Card(CardSuit.HEARTS, CardRank.TEN),
            Card(CardSuit.DIAMONDS, CardRank.TWO),
            Card(CardSuit.CLUBS, CardRank.THREE),
        ]
        best = HandEvaluator.best_hand_from_seven(cards)
        # Should find the royal flush from the hearts
        assert best.hand_type == HandType.ROYAL_FLUSH


class TestCompareMultipleHands:
    """Test cases for comparing multiple hands."""

    def test_compare_multiple_hands(self):
        """Test comparing multiple hands."""
        hands = [
            (0, Hand(HandType.ONE_PAIR, 10, [9, 8], [])),
            (1, Hand(HandType.THREE_OF_A_KIND, 8, [7], [])),
            (2, Hand(HandType.HIGH_CARD, 14, [13, 12, 11], [])),
        ]
        result = HandEvaluator.compare_hands(hands)
        assert result == [1, 0, 2]  # Three of a kind, then pair, then high card


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
