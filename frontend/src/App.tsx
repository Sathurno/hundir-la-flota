import {
  Brain,
  Compass,
  History,
  MousePointer2,
  RefreshCw,
  RotateCcw,
  Ship,
  Shuffle,
  Target,
  Waves,
  type LucideIcon
} from "lucide-react";
import { useEffect, useMemo, useState, type CSSProperties } from "react";
import {
  changeDifficulty,
  createGame,
  placeRandom,
  placeShip,
  resetPlacement,
  rewind,
  shoot
} from "./api";
import type { CellState, Difficulty, GameState, Orientation, TraceEvent } from "./types";

type HoverCell = { row: number; col: number } | null;
type Preview = { keys: Set<string>; valid: boolean };

const DIFFICULTY_COPY: Record<Difficulty, string> = {
  aleatoria: "Dispara casillas libres al azar.",
  caza: "Persigue alrededor de los aciertos.",
  aprendizaje: "Calcula zonas probables con la flota restante."
};

function keyOf(row: number, col: number) {
  return `${row}:${col}`;
}

function statusText(game: GameState | null) {
  if (!game) return "Preparando partida";
  if (game.phase === "placement") return `Colocacion: barco de eslora ${game.nextShip ?? "-"}`;
  if (game.phase === "finished") {
    return game.winner === "jugador" ? "Victoria del jugador" : "Victoria de la IA";
  }
  return `Ronda ${game.turn + 1}`;
}

function cellClass(cell: CellState) {
  if (cell === "O") return "ship";
  if (cell === "X") return "hit";
  if (cell === "A") return "miss";
  if (cell === "H") return "sunk";
  return "empty";
}

function cellLabel(cell: CellState) {
  if (cell === "X") return "X";
  if (cell === "A") return "o";
  if (cell === "H") return "H";
  return "";
}

function jsonLine(value: unknown) {
  try {
    return JSON.stringify(value) ?? String(value);
  } catch {
    return String(value);
  }
}

function App() {
  const [game, setGame] = useState<GameState | null>(null);
  const [orientation, setOrientation] = useState<Orientation>("horizontal");
  const [hover, setHover] = useState<HoverCell>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preferredDifficulty, setPreferredDifficulty] = useState<Difficulty>("caza");

  async function run(action: () => Promise<GameState>) {
    setBusy(true);
    setError(null);
    try {
      const next = await action();
      setGame(next);
      setPreferredDifficulty(next.difficulty);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error inesperado");
    } finally {
      setBusy(false);
    }
  }

  async function startGame(difficulty = preferredDifficulty) {
    await run(() => createGame({ size: 10, difficulty }));
  }

  useEffect(() => {
    void startGame("caza");
  }, []);

  const preview = useMemo<Preview | null>(() => {
    if (!game || game.phase !== "placement" || hover === null || game.nextShip === null) {
      return null;
    }

    const cells = Array.from({ length: game.nextShip }, (_, offset) => {
      if (orientation === "horizontal") {
        return { row: hover.row, col: hover.col + offset };
      }
      return { row: hover.row + offset, col: hover.col };
    });
    const valid = cells.every(
      ({ row, col }) =>
        row >= 0 &&
        row < game.size &&
        col >= 0 &&
        col < game.size &&
        game.boards.player[row][col] === "_"
    );

    return { keys: new Set(cells.map(({ row, col }) => keyOf(row, col))), valid };
  }, [game, hover, orientation]);

  const canPlace = game?.phase === "placement" && !busy;
  const canShoot = game?.phase === "playing" && !busy;

  return (
    <main className="app-shell">
      <div className="ocean-motion" aria-hidden="true" />

      <header className="topbar">
        <div className="brand">
          <Waves aria-hidden="true" />
          <div>
            <h1>Hundir la Flota</h1>
            <p>{statusText(game)}</p>
          </div>
        </div>

        <div className="toolbar">
          <label className="field">
            <Brain size={18} aria-hidden="true" />
            <select
              value={preferredDifficulty}
              disabled={!game || busy}
              onChange={(event) => {
                const difficulty = event.target.value as Difficulty;
                setPreferredDifficulty(difficulty);
                if (game) void run(() => changeDifficulty(game.id, difficulty));
              }}
            >
              {game
                ? (Object.entries(game.difficulties) as Array<[Difficulty, string]>).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))
                : null}
            </select>
          </label>

          <SegmentedOrientation
            orientation={orientation}
            disabled={!canPlace}
            onChange={setOrientation}
          />

          <IconButton
            icon={Shuffle}
            label="Aleatorio"
            disabled={!canPlace || !game}
            onClick={() => game && void run(() => placeRandom(game.id))}
          />
          <IconButton
            icon={RotateCcw}
            label="Limpiar"
            disabled={!canPlace || !game || game.pendingShips.length === game.fleet.length}
            onClick={() => game && void run(() => resetPlacement(game.id))}
          />
          <IconButton
            icon={RefreshCw}
            label="Nueva"
            disabled={busy}
            onClick={() => void startGame()}
          />
        </div>
      </header>

      {error ? <div className="error-banner">{error}</div> : null}

      {game ? (
        <section className="workspace">
          <div className="boards-layout">
            <Board
              title="Tu tablero"
              icon={Ship}
              board={game.boards.player}
              active={game.phase === "placement"}
              remaining={game.remaining.player}
              preview={preview}
              onHover={setHover}
              onLeave={() => setHover(null)}
              onCellClick={(row, col) => {
                if (canPlace) void run(() => placeShip(game.id, { row, col, orientation }));
              }}
            />
            <Board
              title="Tablero IA"
              icon={Target}
              board={game.boards.enemy}
              active={game.phase === "playing"}
              remaining={game.remaining.enemy}
              onCellClick={(row, col, cell) => {
                if (canShoot && cell === "_") void run(() => shoot(game.id, { row, col }));
              }}
            />
          </div>

          <aside className="side-panel">
            <section className="meter-strip">
              <Metric label="Disparos jugador" value={game.shots.player} />
              <Metric label="Disparos IA" value={game.shots.ia} />
              <Metric label="Barcos pendientes" value={game.pendingShips.length} />
            </section>

            <section className="difficulty-note">
              <Brain size={18} aria-hidden="true" />
              <span>{DIFFICULTY_COPY[game.difficulty]}</span>
            </section>

            <TracePanel game={game} busy={busy} onRewind={(index) => run(() => rewind(game.id, index))} />
          </aside>
        </section>
      ) : (
        <section className="loading">
          <RefreshCw aria-hidden="true" />
          <span>Cargando</span>
        </section>
      )}
    </main>
  );
}

function SegmentedOrientation({
  orientation,
  disabled,
  onChange
}: {
  orientation: Orientation;
  disabled: boolean;
  onChange: (value: Orientation) => void;
}) {
  return (
    <div className="segmented" aria-label="Orientacion">
      <button
        type="button"
        className={orientation === "horizontal" ? "selected" : ""}
        disabled={disabled}
        onClick={() => onChange("horizontal")}
      >
        <Compass size={16} aria-hidden="true" />
        Horizontal
      </button>
      <button
        type="button"
        className={orientation === "vertical" ? "selected" : ""}
        disabled={disabled}
        onClick={() => onChange("vertical")}
      >
        <Compass size={16} aria-hidden="true" />
        Vertical
      </button>
    </div>
  );
}

function IconButton({
  icon: Icon,
  label,
  disabled,
  onClick
}: {
  icon: LucideIcon;
  label: string;
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <button type="button" className="icon-button" disabled={disabled} onClick={onClick}>
      <Icon size={17} aria-hidden="true" />
      <span>{label}</span>
    </button>
  );
}

function Board({
  title,
  icon: Icon,
  board,
  active,
  remaining,
  preview,
  onHover,
  onLeave,
  onCellClick
}: {
  title: string;
  icon: LucideIcon;
  board: CellState[][];
  active: boolean;
  remaining: number[];
  preview?: Preview | null;
  onHover?: (cell: HoverCell) => void;
  onLeave?: () => void;
  onCellClick: (row: number, col: number, cell: CellState) => void;
}) {
  const size = board.length;
  const style = { "--board-size": size } as CSSProperties;

  return (
    <section className={`board-panel ${active ? "is-active" : ""}`}>
      <div className="board-heading">
        <h2>
          <Icon size={18} aria-hidden="true" />
          {title}
        </h2>
        <div className="fleet-pips" aria-label="Barcos vivos">
          {remaining.map((ship, index) => (
            <span key={`${ship}-${index}`}>{ship}</span>
          ))}
        </div>
      </div>

      <div className="board-grid" style={style}>
        {board.map((row, rowIndex) =>
          row.map((cell, colIndex) => {
            const key = keyOf(rowIndex, colIndex);
            const inPreview = preview?.keys.has(key) ?? false;
            const classes = [
              "cell",
              `cell-${cellClass(cell)}`,
              inPreview ? (preview?.valid ? "preview-valid" : "preview-invalid") : ""
            ]
              .filter(Boolean)
              .join(" ");

            return (
              <button
                key={key}
                type="button"
                className={classes}
                onMouseEnter={() => onHover?.({ row: rowIndex, col: colIndex })}
                onMouseLeave={onLeave}
                onClick={() => onCellClick(rowIndex, colIndex, cell)}
                aria-label={`${title} fila ${rowIndex} columna ${colIndex}`}
              >
                <span>{cellLabel(cell)}</span>
              </button>
            );
          })
        )}
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function TracePanel({
  game,
  busy,
  onRewind
}: {
  game: GameState;
  busy: boolean;
  onRewind: (index: number) => Promise<void>;
}) {
  return (
    <section className="trace-panel">
      <div className="trace-heading">
        <h2>
          <History size={18} aria-hidden="true" />
          Historial
        </h2>
      </div>

      <div className="timeline">
        {game.history.map((step) => (
          <button
            key={step.index}
            type="button"
            className={step.index === game.historyIndex ? "selected" : ""}
            disabled={busy}
            onClick={() => void onRewind(step.index)}
          >
            <span>{step.index}</span>
            <strong>{step.label}</strong>
          </button>
        ))}
      </div>

      <div className="trace-list">
        {game.trace.map((event) => (
          <TraceItem key={event.id} event={event} />
        ))}
      </div>
    </section>
  );
}

function TraceItem({ event }: { event: TraceEvent }) {
  return (
    <article className={`trace-item actor-${event.actor}`}>
      <div className="trace-meta">
        <span>{event.actor}</span>
        <span>turno {event.turn}</span>
      </div>
      <code>
        {event.funcion}({jsonLine(event.entrada)})
      </code>
      <p>{event.mensaje}</p>
      <div className="trace-result">
        <MousePointer2 size={14} aria-hidden="true" />
        <span>{jsonLine(event.resultado)}</span>
      </div>
    </article>
  );
}

export default App;
