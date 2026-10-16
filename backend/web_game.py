"""Motor de partida reutilizable por la API web.

El modo terminal sigue usando ``backend.main``. Esta capa envuelve las mismas
funciones de tablero e IA en un estado serializable con historial.
"""

from __future__ import annotations

import copy
import inspect
import random
import textwrap
import uuid
from contextlib import contextmanager
from typing import Any, Optional, Union

import numpy as np

from . import utils
from .ia import EstrategiaAleatoria, EstrategiaCaza
from .ia_aprendizaje import EstrategiaAprendizaje

DIFFICULTIES = {
    "aleatoria": "Aleatoria",
    "caza": "Caza",
    "aprendizaje": "Aprendizaje",
}

PHASE_PLACEMENT = "placement"
PHASE_PLAYING = "playing"
PHASE_FINISHED = "finished"

ORIENTATIONS = {"horizontal", "vertical"}


class GameError(ValueError):
    """Error de dominio que la API convierte en respuesta HTTP."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _cell(row: int, col: int) -> tuple[int, int]:
    return int(row), int(col)


def _cell_payload(casilla: tuple[int, int]) -> dict[str, int]:
    return {"row": casilla[0], "col": casilla[1]}


def _cells_payload(
    casillas: Union[list[tuple[int, int]], set[tuple[int, int]]]
) -> list[dict[str, int]]:
    return [_cell_payload(casilla) for casilla in sorted(casillas)]


def _board_payload(tablero: np.ndarray) -> list[list[str]]:
    return tablero.tolist()


def _clone_fleet(flota: list[dict[str, set[tuple[int, int]]]]) -> list[dict[str, set[tuple[int, int]]]]:
    return [
        {"vivas": set(barco["vivas"]), "todas": set(barco["todas"])}
        for barco in flota
    ]


def _fleet_payload(
    flota: list[dict[str, set[tuple[int, int]]]], pending: Optional[list[int]] = None
) -> list[dict[str, Any]]:
    ships = [
        {
            "length": len(barco["todas"]),
            "hits": len(barco["todas"]) - len(barco["vivas"]),
            "sunk": not bool(barco["vivas"]),
            "placed": True,
        }
        for barco in flota
    ]
    for length in pending or []:
        ships.append({"length": length, "hits": 0, "sunk": False, "placed": False})
    return ships


def _strategy_source(strategy: Any) -> str:
    try:
        return textwrap.dedent(inspect.getsource(strategy.__class__.elegir_disparo)).strip()
    except (OSError, TypeError):
        return "def elegir_disparo(self):\n    return self._al_azar()"


class GameSession:
    """Estado completo de una partida web de Hundir la Flota."""

    def __init__(self, size: int = 10, difficulty: str = "caza") -> None:
        self.id = uuid.uuid4().hex
        self.size = self._validate_size(size)
        self.difficulty = self._validate_difficulty(difficulty)
        self.phase = PHASE_PLACEMENT
        self.winner: Optional[str] = None
        self.turn = 0
        self.trace: list[dict[str, Any]] = []
        self.history: list[dict[str, Any]] = []
        self.history_index = -1
        self.ai_shots_log: list[dict[str, Any]] = []
        self.player_shots_log: list[dict[str, Any]] = []
        self.last_ai_decision: Optional[dict[str, Any]] = None
        self._event_seq = 0
        self._rng_state = random.getstate()

        self.player_board = utils.crear_tablero(self.size)
        self.player_fleet: list[dict[str, set[tuple[int, int]]]] = []
        self.player_index: dict[tuple[int, int], dict[str, set[tuple[int, int]]]] = {}

        with self._rng_context():
            self.ai_board, self.ai_fleet, self.ai_index = utils.preparar_bando(self.size)
            self.strategy = self._new_strategy(self.difficulty)

        self._record(
            "Partida creada",
            [
                self._event(
                    "sistema",
                    "GameSession.__init__",
                    {"tamano": self.size, "dificultad": self.difficulty},
                    PHASE_PLACEMENT,
                    "Se prepara el tablero de la IA y queda pendiente colocar tu flota.",
                )
            ],
        )

    @staticmethod
    def _validate_size(size: int) -> int:
        size = int(size)
        if size < 6 or size > 16:
            raise GameError("El tablero debe tener un tamano entre 6 y 16.")
        return size

    @staticmethod
    def _validate_difficulty(difficulty: str) -> str:
        if difficulty not in DIFFICULTIES:
            opciones = ", ".join(DIFFICULTIES)
            raise GameError(f"Dificultad no valida. Usa: {opciones}.")
        return difficulty

    @contextmanager
    def _rng_context(self):
        previous_state = random.getstate()
        random.setstate(self._rng_state)
        try:
            yield
        finally:
            self._rng_state = random.getstate()
            random.setstate(previous_state)

    def _new_strategy(self, difficulty: str):
        if difficulty == "aleatoria":
            return EstrategiaAleatoria(self.size)
        if difficulty == "aprendizaje":
            return EstrategiaAprendizaje(self.size, utils.FLOTA)
        return EstrategiaCaza(self.size)

    def _rebuild_strategy(self, difficulty: str):
        strategy = self._new_strategy(difficulty)
        for shot in self.ai_shots_log:
            barco = None
            if shot["resultado"] == "hundido":
                barco = [tuple(casilla) for casilla in shot.get("barco", [])]
            strategy.registrar(tuple(shot["casilla"]), shot["resultado"], barco)
        return strategy

    def _event(
        self,
        actor: str,
        funcion: str,
        entrada: dict[str, Any],
        resultado: Any,
        mensaje: str,
        cambios: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        self._event_seq += 1
        return {
            "id": self._event_seq,
            "turn": self.turn,
            "actor": actor,
            "funcion": funcion,
            "entrada": entrada,
            "resultado": resultado,
            "mensaje": mensaje,
            "cambios": cambios or [],
        }

    def _record(self, label: str, events: list[dict[str, Any]]) -> None:
        if self.history_index < len(self.history) - 1:
            self.history = self.history[: self.history_index + 1]

        self.trace.extend(events)
        self.history.append(self._snapshot(label, events))
        self.history_index = len(self.history) - 1

    def _snapshot(self, label: str, events: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "label": label,
            "events": copy.deepcopy(events),
            "size": self.size,
            "difficulty": self.difficulty,
            "phase": self.phase,
            "winner": self.winner,
            "turn": self.turn,
            "player_board": self.player_board.copy(),
            "player_fleet": _clone_fleet(self.player_fleet),
            "ai_board": self.ai_board.copy(),
            "ai_fleet": _clone_fleet(self.ai_fleet),
            "strategy": copy.deepcopy(self.strategy),
            "ai_shots_log": copy.deepcopy(self.ai_shots_log),
            "player_shots_log": copy.deepcopy(self.player_shots_log),
            "last_ai_decision": copy.deepcopy(self.last_ai_decision),
            "trace": copy.deepcopy(self.trace),
            "event_seq": self._event_seq,
            "rng_state": copy.deepcopy(self._rng_state),
        }

    def _restore(self, snapshot: dict[str, Any]) -> None:
        self.size = snapshot["size"]
        self.difficulty = snapshot["difficulty"]
        self.phase = snapshot["phase"]
        self.winner = snapshot["winner"]
        self.turn = snapshot["turn"]
        self.player_board = snapshot["player_board"].copy()
        self.player_fleet = _clone_fleet(snapshot["player_fleet"])
        self.player_index = utils.construir_indice(self.player_fleet)
        self.ai_board = snapshot["ai_board"].copy()
        self.ai_fleet = _clone_fleet(snapshot["ai_fleet"])
        self.ai_index = utils.construir_indice(self.ai_fleet)
        self.strategy = copy.deepcopy(snapshot["strategy"])
        self.ai_shots_log = copy.deepcopy(snapshot["ai_shots_log"])
        self.player_shots_log = copy.deepcopy(snapshot["player_shots_log"])
        self.last_ai_decision = copy.deepcopy(snapshot["last_ai_decision"])
        self.trace = copy.deepcopy(snapshot["trace"])
        self._event_seq = snapshot["event_seq"]
        self._rng_state = copy.deepcopy(snapshot["rng_state"])

    def pending_ships(self) -> list[int]:
        return list(utils.FLOTA[len(self.player_fleet) :])

    def _ship_cells(self, row: int, col: int, length: int, orientation: str) -> list[tuple[int, int]]:
        if orientation not in ORIENTATIONS:
            raise GameError("Orientacion no valida. Usa horizontal o vertical.")
        row, col = _cell(row, col)
        if orientation == "horizontal":
            return [(row, col + offset) for offset in range(length)]
        return [(row + offset, col) for offset in range(length)]

    def _assert_cells_fit(self, cells: list[tuple[int, int]]) -> None:
        for row, col in cells:
            if row < 0 or row >= self.size or col < 0 or col >= self.size:
                raise GameError("El barco se sale del tablero.")
            if self.player_board[row, col] != utils.AGUA_VACIA:
                raise GameError("El barco se solapa con otro barco.")

    def place_ship(self, row: int, col: int, orientation: str) -> dict[str, Any]:
        if self.phase != PHASE_PLACEMENT:
            raise GameError("La flota ya esta colocada.")
        pending = self.pending_ships()
        if not pending:
            raise GameError("No quedan barcos pendientes.")

        length = pending[0]
        cells = self._ship_cells(row, col, length, orientation)
        self._assert_cells_fit(cells)
        utils.colocar_barco(cells, self.player_board)
        ship_cells = set(cells)
        self.player_fleet.append({"vivas": set(ship_cells), "todas": set(ship_cells)})
        self.player_index = utils.construir_indice(self.player_fleet)

        events = [
            self._event(
                "jugador",
                "utils.colocar_barco",
                {
                    "origen": _cell_payload(cells[0]),
                    "orientacion": orientation,
                    "eslora": length,
                },
                _cells_payload(cells),
                f"Colocas un barco de eslora {length}.",
                [{"tablero": "jugador", "casillas": _cells_payload(cells), "estado": utils.BARCO}],
            )
        ]
        if not self.pending_ships():
            self.phase = PHASE_PLAYING
            events.append(
                self._event(
                    "sistema",
                    "utils.construir_indice",
                    {"barcos": len(self.player_fleet)},
                    PHASE_PLAYING,
                    "Tu indice de barcos queda listo y empieza la fase de disparos.",
                )
            )

        self._record(f"Barco de eslora {length} colocado", events)
        return self.public_state()

    def random_place_player(self) -> dict[str, Any]:
        if self.phase != PHASE_PLACEMENT:
            raise GameError("Solo puedes recolocar al azar antes de empezar a disparar.")

        with self._rng_context():
            self.player_board, self.player_fleet, self.player_index = utils.preparar_bando(self.size)
        self.phase = PHASE_PLAYING
        events = [
            self._event(
                "jugador",
                "utils.preparar_bando",
                {"tamano": self.size, "flota": list(utils.FLOTA)},
                PHASE_PLAYING,
                "Se coloca toda tu flota al azar y se inicia la partida.",
            )
        ]
        self._record("Flota colocada al azar", events)
        return self.public_state()

    def reset_placement(self) -> dict[str, Any]:
        if self.phase != PHASE_PLACEMENT:
            raise GameError("Solo puedes limpiar la colocacion antes de empezar la partida.")
        self.player_board = utils.crear_tablero(self.size)
        self.player_fleet = []
        self.player_index = {}
        events = [
            self._event(
                "jugador",
                "utils.crear_tablero",
                {"tamano": self.size},
                PHASE_PLACEMENT,
                "Se limpia tu tablero para colocar de nuevo la flota.",
            )
        ]
        self._record("Colocacion reiniciada", events)
        return self.public_state()

    def change_difficulty(self, difficulty: str) -> dict[str, Any]:
        difficulty = self._validate_difficulty(difficulty)
        previous = self.difficulty
        self.difficulty = difficulty
        self.strategy = self._rebuild_strategy(difficulty)
        events = [
            self._event(
                "sistema",
                "crear_estrategia",
                {"anterior": previous, "nueva": difficulty, "disparos_ia": len(self.ai_shots_log)},
                difficulty,
                "La estrategia se reconstruye con los disparos ya conocidos para no repetir casillas.",
            )
        ]
        self._record(f"Dificultad cambiada a {DIFFICULTIES[difficulty]}", events)
        return self.public_state()

    def _predict_ai_target(self) -> Optional[tuple[int, int]]:
        if self.phase != PHASE_PLAYING:
            return None
        previous_state = random.getstate()
        predicted_strategy = copy.deepcopy(self.strategy)
        random.setstate(self._rng_state)
        try:
            return predicted_strategy.elegir_disparo()
        finally:
            random.setstate(previous_state)

    def shoot(self, row: int, col: int) -> dict[str, Any]:
        if self.phase != PHASE_PLAYING:
            raise GameError("La partida no esta en fase de disparos.")
        target = _cell(row, col)
        self._assert_inside(target)

        events: list[dict[str, Any]] = []
        result = utils.disparar(target, self.ai_board, self.ai_index)
        self.player_shots_log.append({"casilla": target, "resultado": result})
        events.append(
            self._event(
                "jugador",
                "utils.disparar",
                {"casilla": _cell_payload(target), "tablero": "ia"},
                result,
                f"Tu disparo en {target[0]},{target[1]} produce: {result}.",
                [{"tablero": "ia", "casilla": _cell_payload(target), "estado": self.ai_board[target]}],
            )
        )

        if result == "repetido":
            self._record("Disparo repetido", events)
            return self.public_state()

        self.turn += 1
        if not utils.quedan_barcos(self.ai_fleet):
            self.phase = PHASE_FINISHED
            self.winner = "jugador"
            events.append(
                self._event(
                    "sistema",
                    "utils.quedan_barcos",
                    {"bando": "ia"},
                    False,
                    "Has hundido toda la flota enemiga.",
                )
            )
            self._record("Victoria del jugador", events)
            return self.public_state()

        with self._rng_context():
            strategy_name = self.strategy.__class__.__name__
            strategy_code = _strategy_source(self.strategy)
            ai_target = self.strategy.elegir_disparo()
            if ai_target is None:
                raise GameError("La IA no encuentra disparos disponibles.", status_code=500)
            events.append(
                self._event(
                    "ia",
                    f"{self.strategy.__class__.__name__}.elegir_disparo",
                    {"dificultad": self.difficulty},
                    _cell_payload(ai_target),
                    "La IA elige su siguiente casilla.",
                )
            )
            ai_result = utils.disparar(ai_target, self.player_board, self.player_index)
            sunk_ship = sorted(self.player_index[ai_target]["todas"]) if ai_result == "hundido" else []
            self.strategy.registrar(ai_target, ai_result, sunk_ship or None)
            self.last_ai_decision = {
                "difficulty": self.difficulty,
                "strategy": strategy_name,
                "function": f"{strategy_name}.elegir_disparo",
                "code": strategy_code,
                "chosen": _cell_payload(ai_target),
                "result": ai_result,
                "message": (
                    f"La IA uso {strategy_name}.elegir_disparo y eligio "
                    f"fila {ai_target[0]}, columna {ai_target[1]}."
                ),
            }
            self.ai_shots_log.append(
                {"casilla": ai_target, "resultado": ai_result, "barco": list(sunk_ship)}
            )
            events.append(
                self._event(
                    "ia",
                    "utils.disparar",
                    {"casilla": _cell_payload(ai_target), "tablero": "jugador"},
                    ai_result,
                    f"La IA dispara en {ai_target[0]},{ai_target[1]} y obtiene: {ai_result}.",
                    [
                        {
                            "tablero": "jugador",
                            "casilla": _cell_payload(ai_target),
                            "estado": self.player_board[ai_target],
                        }
                    ],
                )
            )
            events.append(
                self._event(
                    "ia",
                    f"{self.strategy.__class__.__name__}.registrar",
                    {"casilla": _cell_payload(ai_target), "resultado": ai_result},
                    "actualizado",
                    "La IA actualiza su memoria interna con el resultado del disparo.",
                )
            )

        if not utils.quedan_barcos(self.player_fleet):
            self.phase = PHASE_FINISHED
            self.winner = "ia"
            events.append(
                self._event(
                    "sistema",
                    "utils.quedan_barcos",
                    {"bando": "jugador"},
                    False,
                    "La IA ha hundido toda tu flota.",
                )
            )

        self._record(f"Ronda {self.turn}: disparo a {target[0]},{target[1]}", events)
        return self.public_state()

    def rewind(self, history_index: int) -> dict[str, Any]:
        history_index = int(history_index)
        if history_index < 0 or history_index >= len(self.history):
            raise GameError("Paso de historial no valido.")
        self.history_index = history_index
        self._restore(self.history[history_index])
        return self.public_state()

    def _assert_inside(self, casilla: tuple[int, int]) -> None:
        row, col = casilla
        if row < 0 or row >= self.size or col < 0 or col >= self.size:
            raise GameError("La casilla esta fuera del tablero.")

    def public_state(self) -> dict[str, Any]:
        enemy_board = self.ai_board if self.phase == PHASE_FINISHED else utils.ocultar_barcos(self.ai_board)
        pending = self.pending_ships()
        next_ai_target = self._predict_ai_target()
        return {
            "id": self.id,
            "size": self.size,
            "phase": self.phase,
            "winner": self.winner,
            "turn": self.turn,
            "difficulty": self.difficulty,
            "difficultyLabel": DIFFICULTIES[self.difficulty],
            "difficulties": DIFFICULTIES,
            "fleet": list(utils.FLOTA),
            "pendingShips": pending,
            "nextShip": pending[0] if pending else None,
            "boards": {
                "player": _board_payload(self.player_board),
                "enemy": _board_payload(enemy_board),
            },
            "remaining": {
                "player": utils.barcos_vivos(self.player_fleet),
                "enemy": utils.barcos_vivos(self.ai_fleet),
            },
            "fleetStatus": {
                "player": _fleet_payload(self.player_fleet, pending),
                "enemy": _fleet_payload(self.ai_fleet),
            },
            "lastAiDecision": self.last_ai_decision,
            "nextAiTarget": _cell_payload(next_ai_target) if next_ai_target else None,
            "historyIndex": self.history_index,
            "history": [
                {
                    "index": index,
                    "label": snapshot["label"],
                    "phase": snapshot["phase"],
                    "winner": snapshot["winner"],
                    "turn": snapshot["turn"],
                    "events": snapshot["events"],
                }
                for index, snapshot in enumerate(self.history)
            ],
            "trace": self.trace,
            "shots": {
                "player": len([shot for shot in self.player_shots_log if shot["resultado"] != "repetido"]),
                "ia": len(self.ai_shots_log),
            },
        }
