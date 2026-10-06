import type { Difficulty, GameState, Orientation } from "./types";

const API_BASE = import.meta.env.VITE_API_URL ?? "";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {})
    }
  });

  if (!response.ok) {
    let message = `Error HTTP ${response.status}`;
    try {
      const data = (await response.json()) as { detail?: string };
      message = data.detail ?? message;
    } catch {
      // Keep the generic message.
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export function createGame(payload: { size: number; difficulty: Difficulty }) {
  return request<GameState>("/api/games", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function placeShip(
  gameId: string,
  payload: { row: number; col: number; orientation: Orientation }
) {
  return request<GameState>(`/api/games/${gameId}/place`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function placeRandom(gameId: string) {
  return request<GameState>(`/api/games/${gameId}/place/random`, {
    method: "POST"
  });
}

export function resetPlacement(gameId: string) {
  return request<GameState>(`/api/games/${gameId}/place/reset`, {
    method: "POST"
  });
}

export function changeDifficulty(gameId: string, difficulty: Difficulty) {
  return request<GameState>(`/api/games/${gameId}/difficulty`, {
    method: "POST",
    body: JSON.stringify({ difficulty })
  });
}

export function shoot(gameId: string, payload: { row: number; col: number }) {
  return request<GameState>(`/api/games/${gameId}/shot`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function rewind(gameId: string, index: number) {
  return request<GameState>(`/api/games/${gameId}/rewind`, {
    method: "POST",
    body: JSON.stringify({ index })
  });
}
