import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import utils
from backend.web_game import GameError, GameSession, PHASE_FINISHED, PHASE_PLACEMENT, PHASE_PLAYING


def assert_raises_game_error(func):
    try:
        func()
    except GameError:
        return
    raise AssertionError("se esperaba GameError")


def first_ship_cell(game):
    for row in range(game.size):
        for col in range(game.size):
            if game.ai_board[row, col] == utils.BARCO:
                return row, col
    raise AssertionError("no hay barcos en el tablero de la IA")


def first_unshot_cell(game, forbidden=None):
    forbidden = forbidden or set()
    fired = {tuple(shot["casilla"]) for shot in game.player_shots_log}
    for row in range(game.size):
        for col in range(game.size):
            if (row, col) not in fired and (row, col) not in forbidden:
                return row, col
    raise AssertionError("no quedan casillas libres")


def ready_game(difficulty="caza"):
    random.seed(11)
    game = GameSession(size=10, difficulty=difficulty)
    game.random_place_player()
    return game


def test_manual_placement_rejects_invalid_cells_and_starts_game():
    random.seed(1)
    game = GameSession(size=6, difficulty="aleatoria")
    assert game.phase == PHASE_PLACEMENT

    game.place_ship(0, 0, "horizontal")
    assert_raises_game_error(lambda: game.place_ship(0, 1, "horizontal"))
    assert_raises_game_error(lambda: game.place_ship(5, 5, "horizontal"))

    game.place_ship(1, 0, "horizontal")
    game.place_ship(2, 0, "horizontal")
    game.place_ship(3, 0, "horizontal")
    game.place_ship(4, 0, "horizontal")
    state = game.place_ship(5, 0, "horizontal")

    assert state["phase"] == PHASE_PLAYING
    assert len(game.player_fleet) == len(utils.FLOTA)
    assert sum(len(ship["todas"]) for ship in game.player_fleet) == sum(utils.FLOTA)


def test_random_placement_completes_player_fleet():
    game = GameSession(size=10, difficulty="caza")
    state = game.random_place_player()

    assert state["phase"] == PHASE_PLAYING
    assert len(game.player_fleet) == len(utils.FLOTA)
    assert len(state["fleetStatus"]["player"]) == len(utils.FLOTA)
    assert state["nextShip"] is None


def test_player_shot_triggers_ai_response_and_trace():
    game = ready_game()
    row, col = first_ship_cell(game)

    state = game.shoot(row, col)

    assert state["phase"] in (PHASE_PLAYING, PHASE_FINISHED)
    assert state["turn"] == 1
    assert len(game.ai_shots_log) == 1
    assert state["lastAiDecision"]["chosen"] == {
        "row": game.ai_shots_log[-1]["casilla"][0],
        "col": game.ai_shots_log[-1]["casilla"][1],
    }
    assert state["nextAiTarget"] is not None
    assert any(event["funcion"] == "utils.disparar" for event in state["trace"])


def test_fleet_status_keeps_sunk_ships_visible():
    game = ready_game()
    target_ship = sorted(game.ai_fleet[0]["todas"])
    state = None
    for row, col in target_ship:
        state = game.shoot(row, col)

    assert state is not None
    assert len(state["fleetStatus"]["enemy"]) == len(utils.FLOTA)
    assert any(ship["sunk"] for ship in state["fleetStatus"]["enemy"])


def test_difficulty_change_rebuilds_strategy_without_repeating_ai_shots():
    game = ready_game("caza")
    for _ in range(3):
        row, col = first_unshot_cell(game)
        game.shoot(row, col)

    fired_by_ai = {tuple(shot["casilla"]) for shot in game.ai_shots_log}
    game.change_difficulty("aleatoria")

    assert all(casilla not in game.strategy.posicion for casilla in fired_by_ai)
    assert game.strategy.elegir_disparo() not in fired_by_ai


def test_rewind_restores_state_and_next_action_branches_history():
    game = ready_game()
    first_target = first_ship_cell(game)
    game.shoot(*first_target)
    original_history_len = len(game.history)

    game.rewind(1)
    assert game.turn == 0
    assert game.history_index == 1

    game.shoot(*first_unshot_cell(game, forbidden={first_target}))
    assert len(game.history) == original_history_len
    assert game.history_index == len(game.history) - 1
    assert tuple(game.player_shots_log[0]["casilla"]) != first_target


def test_terminal_entrypoint_still_imports():
    import play

    assert callable(play.main)


if __name__ == "__main__":
    test_manual_placement_rejects_invalid_cells_and_starts_game()
    test_random_placement_completes_player_fleet()
    test_player_shot_triggers_ai_response_and_trace()
    test_fleet_status_keeps_sunk_ships_visible()
    test_difficulty_change_rebuilds_strategy_without_repeating_ai_shots()
    test_rewind_restores_state_and_next_action_branches_history()
    test_terminal_entrypoint_still_imports()
    print("OK")
