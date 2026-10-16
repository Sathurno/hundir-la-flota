export type CellState = "_" | "O" | "X" | "A" | "H";
export type Difficulty = "aleatoria" | "caza" | "aprendizaje";
export type Orientation = "horizontal" | "vertical";
export type Phase = "placement" | "playing" | "finished";
export type Winner = "jugador" | "ia" | null;

export interface TraceEvent {
  id: number;
  turn: number;
  actor: string;
  funcion: string;
  entrada: Record<string, unknown>;
  resultado: unknown;
  mensaje: string;
  cambios: Array<Record<string, unknown>>;
}

export interface HistoryStep {
  index: number;
  label: string;
  phase: Phase;
  winner: Winner;
  turn: number;
  events: TraceEvent[];
}

export interface CellCoord {
  row: number;
  col: number;
}

export interface FleetShip {
  length: number;
  hits: number;
  sunk: boolean;
  placed: boolean;
}

export interface AiDecision {
  difficulty: Difficulty;
  strategy: string;
  function: string;
  code: string;
  chosen: CellCoord;
  result: string;
  message: string;
}

export interface GameState {
  id: string;
  size: number;
  phase: Phase;
  winner: Winner;
  turn: number;
  difficulty: Difficulty;
  difficultyLabel: string;
  difficulties: Record<Difficulty, string>;
  fleet: number[];
  pendingShips: number[];
  nextShip: number | null;
  boards: {
    player: CellState[][];
    enemy: CellState[][];
  };
  remaining: {
    player: number[];
    enemy: number[];
  };
  fleetStatus: {
    player: FleetShip[];
    enemy: FleetShip[];
  };
  lastAiDecision: AiDecision | null;
  nextAiTarget: CellCoord | null;
  historyIndex: number;
  history: HistoryStep[];
  trace: TraceEvent[];
  shots: {
    player: number;
    ia: number;
  };
}
