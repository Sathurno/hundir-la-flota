"""API local para jugar Hundir la Flota desde la web."""

from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .web_game import GameError, GameSession

app = FastAPI(title="Hundir la Flota API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSIONS: dict[str, GameSession] = {}


class CreateGameRequest(BaseModel):
    size: int = 10
    difficulty: str = "caza"


class PlaceShipRequest(BaseModel):
    row: int
    col: int
    orientation: str


class DifficultyRequest(BaseModel):
    difficulty: str


class ShotRequest(BaseModel):
    row: int
    col: int


class RewindRequest(BaseModel):
    index: int


@app.exception_handler(GameError)
async def handle_game_error(_, exc: GameError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


def _get_game(game_id: str) -> GameSession:
    game = SESSIONS.get(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Partida no encontrada.")
    return game


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/games")
def create_game(payload: Optional[CreateGameRequest] = None):
    data = payload or CreateGameRequest()
    game = GameSession(size=data.size, difficulty=data.difficulty)
    SESSIONS[game.id] = game
    return game.public_state()


@app.get("/api/games/{game_id}")
def get_game(game_id: str):
    return _get_game(game_id).public_state()


@app.post("/api/games/{game_id}/place")
def place_ship(game_id: str, payload: PlaceShipRequest):
    return _get_game(game_id).place_ship(payload.row, payload.col, payload.orientation)


@app.post("/api/games/{game_id}/place/random")
def place_random(game_id: str):
    return _get_game(game_id).random_place_player()


@app.post("/api/games/{game_id}/place/reset")
def reset_placement(game_id: str):
    return _get_game(game_id).reset_placement()


@app.post("/api/games/{game_id}/difficulty")
def change_difficulty(game_id: str, payload: DifficultyRequest):
    return _get_game(game_id).change_difficulty(payload.difficulty)


@app.post("/api/games/{game_id}/shot")
def shoot(game_id: str, payload: ShotRequest):
    return _get_game(game_id).shoot(payload.row, payload.col)


@app.post("/api/games/{game_id}/rewind")
def rewind(game_id: str, payload: RewindRequest):
    return _get_game(game_id).rewind(payload.index)
