// pybind11 module exposing the C++ engine to Python as `poker_engine`.
//
// A thin translation layer: no rules logic lives here. Names follow Python
// conventions (snake_case members, UPPER_SNAKE enum values), and
// argument-free getters become read-only properties.
//
// Ownership: objects that can disappear while Python still holds them -
// a `Player` (its seat can be emptied) and a street's `BettingRound`
// (replaced every street) - are returned as snapshots (copies), never as
// live references. `GameController.table` and `Table.deck` are live, since
// their owner never replaces them.
//
// C++ exceptions map to Python ones via pybind11's defaults:
// std::invalid_argument -> ValueError, std::out_of_range -> IndexError,
// std::logic_error -> RuntimeError.

#include <pybind11/operators.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "poker/action.hpp"
#include "poker/betting_round.hpp"
#include "poker/card.hpp"
#include "poker/deck.hpp"
#include "poker/game_controller.hpp"
#include "poker/hand_evaluator.hpp"
#include "poker/player.hpp"
#include "poker/pot_manager.hpp"
#include "poker/showdown.hpp"
#include "poker/table.hpp"

namespace py = pybind11;
using namespace poker;

namespace {

std::optional<Player> playerSnapshot(const Player* player) {
    return player ? std::optional<Player>(*player) : std::nullopt;
}

std::vector<Player> playerSnapshots(const std::vector<Player*>& players) {
    std::vector<Player> result;
    result.reserve(players.size());
    for (const Player* player : players) {
        result.push_back(*player);
    }
    return result;
}

}  // namespace

PYBIND11_MODULE(poker_engine, m) {
    m.doc() = "Texas Hold'em rules engine (C++), exposed to Python via pybind11.";

    // -- Enums ---------------------------------------------------------------
    // Rank and HandType are ordered (and convertible to int), so they
    // support <, >, etc.; the rest compare by equality only.

    py::enum_<Suit>(m, "Suit")
        .value("HEARTS", Suit::Hearts)
        .value("DIAMONDS", Suit::Diamonds)
        .value("CLUBS", Suit::Clubs)
        .value("SPADES", Suit::Spades);

    py::enum_<Rank>(m, "Rank", py::arithmetic())
        .value("TWO", Rank::Two)
        .value("THREE", Rank::Three)
        .value("FOUR", Rank::Four)
        .value("FIVE", Rank::Five)
        .value("SIX", Rank::Six)
        .value("SEVEN", Rank::Seven)
        .value("EIGHT", Rank::Eight)
        .value("NINE", Rank::Nine)
        .value("TEN", Rank::Ten)
        .value("JACK", Rank::Jack)
        .value("QUEEN", Rank::Queen)
        .value("KING", Rank::King)
        .value("ACE", Rank::Ace);

    py::enum_<HandType>(m, "HandType", py::arithmetic())
        .value("HIGH_CARD", HandType::HighCard)
        .value("ONE_PAIR", HandType::OnePair)
        .value("TWO_PAIR", HandType::TwoPair)
        .value("THREE_OF_A_KIND", HandType::ThreeOfAKind)
        .value("STRAIGHT", HandType::Straight)
        .value("FLUSH", HandType::Flush)
        .value("FULL_HOUSE", HandType::FullHouse)
        .value("FOUR_OF_A_KIND", HandType::FourOfAKind)
        .value("STRAIGHT_FLUSH", HandType::StraightFlush)
        .value("ROYAL_FLUSH", HandType::RoyalFlush);

    py::enum_<ActionType>(m, "ActionType")
        .value("FOLD", ActionType::Fold)
        .value("CHECK", ActionType::Check)
        .value("CALL", ActionType::Call)
        .value("BET", ActionType::Bet)
        .value("RAISE", ActionType::Raise)
        .value("ALL_IN", ActionType::AllIn);

    py::enum_<PlayerStatus>(m, "PlayerStatus")
        .value("ACTIVE", PlayerStatus::Active)
        .value("FOLDED", PlayerStatus::Folded)
        .value("ALL_IN", PlayerStatus::AllIn)
        .value("SITTING_OUT", PlayerStatus::SittingOut);

    py::enum_<Street>(m, "Street")
        .value("PRE_FLOP", Street::PreFlop)
        .value("FLOP", Street::Flop)
        .value("TURN", Street::Turn)
        .value("RIVER", Street::River)
        .value("SHOWDOWN", Street::Showdown)
        .value("HAND_COMPLETE", Street::HandComplete);

    py::enum_<ProgressionMode>(m, "ProgressionMode")
        .value("AUTO", ProgressionMode::Auto)
        .value("SINGLE_STEP", ProgressionMode::SingleStep);

    py::enum_<HandPhase>(m, "HandPhase")
        .value("NOT_STARTED", HandPhase::NotStarted)
        .value("AWAITING_ACTION", HandPhase::AwaitingAction)
        .value("PENDING_ADVANCE", HandPhase::PendingAdvance)
        .value("HAND_COMPLETE", HandPhase::HandComplete);

    m.def("street_number", &streetNumber, py::arg("street"),
          "0-4 for PRE_FLOP..SHOWDOWN, -1 for HAND_COMPLETE.");

    // -- Cards ---------------------------------------------------------------

    py::class_<Card>(m, "Card", "An immutable playing card. Orders by rank only; equality needs suit too.")
        .def(py::init<Suit, Rank>(), py::arg("suit"), py::arg("rank"))
        .def_property_readonly("suit", &Card::suit)
        .def_property_readonly("rank", &Card::rank)
        .def_property_readonly("rank_value", &Card::rankValue, "Rank strength, 2-14.")
        .def("__str__", &Card::toString)
        .def("__repr__",
             [](const Card& card) {
                 return py::str("Card({}, {})").format(py::cast(card.suit()), py::cast(card.rank()));
             })
        .def(py::self == py::self)
        .def(py::self != py::self)
        .def(py::self < py::self)
        .def(py::self <= py::self)
        .def(py::self > py::self)
        .def(py::self >= py::self)
        .def("__hash__", [](const Card& card) { return std::hash<Card>{}(card); });

    py::class_<Deck> deck(m, "Deck", "A standard 52-card deck, dealt from the top.");
    deck.attr("FULL_DECK_SIZE") = Deck::kFullDeckSize;
    deck.def(py::init<>())
        .def("reset", &Deck::reset, "Restores all 52 cards in canonical (unshuffled) order.")
        .def("shuffle", &Deck::shuffle)
        .def("seed", &Deck::seed, py::arg("value"), "Reseeds the shuffle RNG, for deterministic shuffles.")
        .def("put_on_top", &Deck::putOnTop, py::arg("cards"),
             "Moves `cards` to the top so they're dealt next, cards[0] first. "
             "Raises ValueError (deck unchanged) if a card is missing or repeated.")
        .def("deal_card", &Deck::dealCard, "Raises IndexError if the deck is empty.")
        .def("peek_card", &Deck::peekCard, "Raises IndexError if the deck is empty.")
        .def_property_readonly("remaining", &Deck::remaining)
        .def_property_readonly("is_empty", &Deck::isEmpty)
        .def("__len__", &Deck::remaining);

    // -- Hand evaluation -----------------------------------------------------

    py::class_<Hand>(m, "Hand", "An evaluated 5-card hand. Compares by strength.")
        .def_property_readonly("hand_type", &Hand::type)
        .def_property_readonly("rank_value", &Hand::rankValue)
        .def_property_readonly("kickers", &Hand::kickers)
        .def_property_readonly("cards", &Hand::cards)
        .def(py::self == py::self)
        .def(py::self != py::self)
        .def(py::self < py::self)
        .def(py::self <= py::self)
        .def(py::self > py::self)
        .def(py::self >= py::self)
        .def("__repr__", [](const Hand& hand) {
            return py::str("Hand({}, rank_value={}, kickers={})")
                .format(py::cast(hand.type()), hand.rankValue(), py::cast(hand.kickers()));
        });

    py::class_<HandEvaluator>(m, "HandEvaluator")
        .def_static("evaluate_hand", &HandEvaluator::evaluateHand, py::arg("cards"),
                    "Evaluates exactly 5 cards (ValueError otherwise).")
        .def_static("best_hand_from_seven", &HandEvaluator::bestHandFromSeven, py::arg("cards"),
                    "Best 5-card hand from exactly 7 cards (ValueError otherwise).");

    // -- Actions and players -------------------------------------------------

    py::class_<Action>(m, "Action",
                       "One player action. BET amounts are chips put in; RAISE amounts are "
                       "'raise by' on top of the call; CALL/ALL_IN amounts are ignored.")
        .def(py::init<ActionType, int, int>(), py::arg("action_type"), py::arg("player_seat"),
             py::arg("amount") = 0)
        .def_property_readonly("action_type", &Action::type)
        .def_property_readonly("player_seat", &Action::playerSeat)
        .def_property_readonly("amount", &Action::amount)
        .def(py::self == py::self)
        .def(py::self != py::self)
        .def("__repr__", [](const Action& action) {
            return py::str("Action({}, player_seat={}, amount={})")
                .format(py::cast(action.type()), action.playerSeat(), action.amount());
        });

    py::class_<Player>(m, "Player",
                       "A seated player. Players read from a Table are snapshots: re-read them "
                       "after the game moves on.")
        .def(py::init<std::string, int, int>(), py::arg("name"), py::arg("seat"), py::arg("initial_stack"))
        .def_property_readonly("name", &Player::name)
        .def_property_readonly("seat", &Player::seat)
        .def_property_readonly("stack", &Player::stack)
        .def_property_readonly("hole_cards", &Player::holeCards)
        .def_property_readonly("status", &Player::status)
        .def_property_readonly("current_bet", &Player::currentBet, "Chips put in so far this hand.")
        .def_property_readonly("has_chips", &Player::hasChips)
        .def_property_readonly("is_active", &Player::isActive, "Still in the hand (ACTIVE or ALL_IN).")
        .def_property_readonly("can_act", &Player::canAct, "ACTIVE, i.e. can still choose an action.")
        .def("__repr__", [](const Player& player) {
            return py::str("Player({!r}, seat={}, stack={}, status={})")
                .format(player.name(), player.seat(), player.stack(), py::cast(player.status()));
        });

    // -- Table ---------------------------------------------------------------
    // Seating and read-only state. Per-hand mutators (dealing, blinds,
    // street advancement, pot updates) are GameController's job and aren't
    // bound.

    py::class_<Table> table(m, "Table");
    table.attr("MAX_PLAYERS") = Table::kMaxPlayers;
    table.def(py::init<int>(), py::arg("num_seats"), "ValueError unless 2 <= num_seats <= MAX_PLAYERS.")
        .def_property_readonly("num_seats", &Table::numSeats)
        .def("add_player", &Table::addPlayer, py::arg("player"),
             "Seats a copy of `player` at player.seat (ValueError if invalid or occupied).")
        .def("remove_player", &Table::removePlayer, py::arg("seat"),
             "Removes and returns the player at `seat`, or None if it was empty.")
        .def(
            "get_player", [](const Table& t, int seat) { return playerSnapshot(t.getPlayer(seat)); },
            py::arg("seat"), "Snapshot of the player at `seat`, or None.")
        .def(
            "get_active_players", [](Table& t) { return playerSnapshots(t.getActivePlayers()); },
            "Snapshots of players still in the hand (ACTIVE or ALL_IN), in seat order.")
        .def(
            "get_all_players", [](Table& t) { return playerSnapshots(t.getAllPlayers()); },
            "Snapshots of every seated player, in seat order.")
        .def("get_next_active_player", &Table::getNextActivePlayer, py::arg("from_seat"),
             "Next seat after `from_seat` (wrapping) whose player can act, or None.")
        .def("get_previous_active_player", &Table::getPreviousActivePlayer, py::arg("from_seat"))
        .def_property_readonly(
            "deck", [](Table& t) -> Deck& { return t.deck(); }, "The table's live deck (e.g. to seed it).")
        .def_property_readonly("street", &Table::street)
        .def_property_readonly("community_cards", &Table::communityCards)
        .def_property_readonly("burned_cards", &Table::burnedCards)
        .def_property_readonly("total_pot", &Table::totalPot)
        .def_property_readonly("current_player_seat", &Table::currentPlayerSeat)
        .def_property_readonly("button_seat", &Table::buttonSeat)
        .def_property_readonly("small_blind_seat", &Table::smallBlindSeat)
        .def_property_readonly("big_blind_seat", &Table::bigBlindSeat)
        .def_property_readonly("small_blind_amount", &Table::smallBlindAmount)
        .def_property_readonly("big_blind_amount", &Table::bigBlindAmount)
        .def("is_button", &Table::isButton, py::arg("seat"))
        .def("is_small_blind", &Table::isSmallBlind, py::arg("seat"))
        .def("is_big_blind", &Table::isBigBlind, py::arg("seat"));

    // -- Betting, pots, and results (all read-only) --------------------------

    py::class_<BettingRound>(m, "BettingRound",
                             "Snapshot of one street's betting, from GameController.betting_round.")
        .def_property_readonly("actions", &BettingRound::actions)
        .def_property_readonly("highest_bet", &BettingRound::highestBet)
        .def_property_readonly("min_raise_amount", &BettingRound::minRaiseAmount)
        .def_property_readonly("player_bet_amounts", &BettingRound::playerBetAmounts,
                               "{seat: chips put in this street}.")
        .def_property_readonly("is_round_complete", &BettingRound::isRoundComplete)
        .def("get_amount_to_call", &BettingRound::getAmountToCall, py::arg("seat"))
        .def("can_check", &BettingRound::canCheck, py::arg("seat"))
        .def("is_capped", &BettingRound::isCapped, py::arg("seat"))
        .def("get_players_all_in", &BettingRound::getPlayersAllIn);

    py::class_<Pot>(m, "Pot")
        .def_readonly("amount", &Pot::amount)
        .def_readonly("eligible_seats", &Pot::eligibleSeats)
        .def("__repr__", [](const Pot& pot) {
            return py::str("Pot(amount={}, eligible_seats={})").format(pot.amount, py::cast(pot.eligibleSeats));
        });

    py::class_<PlayerResult>(m, "PlayerResult")
        .def_property_readonly("seat", &PlayerResult::seat)
        .def_property_readonly("name", &PlayerResult::name)
        .def_property_readonly("hole_cards", &PlayerResult::holeCards)
        .def_property_readonly("best_hand", &PlayerResult::bestHand, "None if the hand ended without a showdown.")
        .def_property_readonly("chips_won", &PlayerResult::chipsWon)
        .def("__repr__", [](const PlayerResult& r) {
            return py::str("PlayerResult(seat={}, name={!r}, chips_won={})").format(r.seat(), r.name(), r.chipsWon());
        });

    py::class_<ShowdownResult>(m, "ShowdownResult")
        .def_property_readonly("player_results", &ShowdownResult::playerResults)
        .def_property_readonly("is_showdown", &ShowdownResult::isShowdown,
                               "False when everyone else folded and nobody showed cards.")
        .def_property_readonly("winners", &ShowdownResult::winners, "Results of players who won chips.")
        .def_property_readonly("total_pot", &ShowdownResult::totalPot);

    py::class_<LegalActions>(m, "LegalActions",
                             "What the seat on the clock may do. min/max_raise are 'raise by' amounts.")
        .def_readonly("seat", &LegalActions::seat)
        .def_readonly("can_fold", &LegalActions::canFold)
        .def_readonly("can_check", &LegalActions::canCheck)
        .def_readonly("can_call", &LegalActions::canCall)
        .def_readonly("call_amount", &LegalActions::callAmount)
        .def_readonly("can_bet", &LegalActions::canBet)
        .def_readonly("min_bet", &LegalActions::minBet)
        .def_readonly("max_bet", &LegalActions::maxBet)
        .def_readonly("can_raise", &LegalActions::canRaise)
        .def_readonly("min_raise", &LegalActions::minRaise)
        .def_readonly("max_raise", &LegalActions::maxRaise)
        .def_readonly("can_all_in", &LegalActions::canAllIn)
        .def_readonly("all_in_amount", &LegalActions::allInAmount);

    // -- GameController ------------------------------------------------------

    py::class_<GameController>(m, "GameController",
                               "Runs hands on its own copy of the table given to it - use "
                               "`controller.table` afterwards, not the original.")
        .def(py::init<Table, int, int, ProgressionMode>(), py::arg("table"), py::arg("small_blind_amount"),
             py::arg("big_blind_amount"), py::arg("mode") = ProgressionMode::Auto)
        .def_property_readonly(
            "table", [](GameController& g) -> Table& { return g.table(); }, "The controller's live table.")
        .def_property_readonly("small_blind_amount", &GameController::smallBlindAmount)
        .def_property_readonly("big_blind_amount", &GameController::bigBlindAmount)
        .def_property("mode", &GameController::mode, &GameController::setMode)
        .def_property_readonly("phase", &GameController::phase)
        .def_property_readonly("is_hand_complete", &GameController::isHandComplete)
        .def_property_readonly("hand_number", &GameController::handNumber)
        .def_property_readonly("current_seat", &GameController::currentSeat,
                               "Seat that must act, or None unless phase is AWAITING_ACTION.")
        .def("start_hand", &GameController::startHand, py::arg("stacked_cards") = std::vector<Card>{},
             "Starts a new hand. `stacked_cards` are dealt first: two to each player in seat order, "
             "then burn + flop, burn + turn, burn + river. RuntimeError if a hand is in progress or "
             "fewer than 2 players have chips; ValueError if a stacked card repeats.")
        .def("legal_actions", &GameController::legalActions, "RuntimeError unless phase is AWAITING_ACTION.")
        .def("validate_action", &GameController::validateAction, py::arg("action"),
             "Why `action` is illegal right now, or None if it's legal. Never changes state.")
        .def("submit_action", &GameController::submitAction, py::arg("action"),
             "Applies `action` for the seat on the clock (ValueError if illegal, RuntimeError if no one "
             "is on the clock). In AUTO mode, also runs the transitions that follow.")
        .def("step_once", &GameController::stepOnce,
             "Runs one pending transition (deal a street or resolve the hand). False if none pending.")
        .def("advance", &GameController::advance, "Runs transitions until a player must act or the hand ends.")
        .def_property_readonly(
            "betting_round",
            [](const GameController& g) -> std::optional<BettingRound> {
                const BettingRound* round = g.bettingRound();
                return round ? std::optional<BettingRound>(*round) : std::nullopt;
            },
            "Snapshot of the current street's betting, or None between streets and hands.")
        .def_property_readonly("contributions", &GameController::contributions,
                               "{seat: chips put in this hand}, blinds included.")
        .def_property_readonly(
            "pots", [](const GameController& g) { return g.potManager().pots(); },
            "Main pot then side pots, once the hand is resolved.")
        .def_property_readonly("last_result", &GameController::lastResult,
                               "Outcome of the last completed hand, or None.");
}
