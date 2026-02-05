"""
FastAPI server for tank game control.

Mirrors the pattern in api_server.py: global queue refs + uvicorn.
Exposes per-tank command endpoints and a shared game state GET.

Usage:
    Started as a daemon thread from __main__.py.

    Example requests:
        POST /player1/command {"command": "forward"}
        POST /player1/command {"command": "shoot"}
        POST /player2/command {"command": "rotate_left"}
        GET  /state
"""
from queue import Queue
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from typing import List

from tanks.constants import TankCommand
from tanks.command_system import parse_command

app = FastAPI(
    title="Tank Arena API",
    description="Control tanks via HTTP requests",
    version="1.0.0",
)

# Global references -- set by run_tank_api()
_p1_queue: Optional[Queue] = None
_p2_queue: Optional[Queue] = None
_game_state = None
_game_history = None


class TankCommandRequest(BaseModel):
    """Request body for tank command endpoints."""
    command: str

    class Config:
        json_schema_extra = {
            "examples": [
                {"command": "forward"},
                {"command": "shoot"},
                {"command": "rotate_left"},
                {"command": "auto_shoot_on"},
                {"command": "auto_shoot_off"},
            ]
        }


class TankCommandResponse(BaseModel):
    """Response from tank command endpoints."""
    status: str
    command: str
    player: int


class StrategyRequest(BaseModel):
    """Request body for natural language strategy endpoints."""
    text: str

    class Config:
        json_schema_extra = {
            "examples": [
                {"text": "patrol between B2 and B9 and shoot at anything in your sight"},
                {"text": "guard position E5"},
                {"text": "move to I6"},
                {"text": "stop"},
            ]
        }


class StrategyResponse(BaseModel):
    """Response from strategy endpoints."""
    status: str
    text: str
    parsed: List[dict]
    player: int


def _validate_command(raw: str) -> TankCommand:
    try:
        return TankCommand(raw.strip().lower())
    except ValueError:
        valid = [c.value for c in TankCommand]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid command '{raw}'. Valid commands: {valid}",
        )


@app.get("/")
def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Tank Arena API is running"}


@app.get("/state")
def get_state():
    """Return full game state snapshot."""
    if _game_state is None:
        raise HTTPException(status_code=503, detail="Game not initialized")
    return _game_state.snapshot()


@app.get("/log")
def get_log(since_tick: Optional[int] = None, limit: Optional[int] = 100):
    """Return game history including commands and periodic snapshots.

    Query parameters:
    - since_tick: Only return entries after this tick (optional)
    - limit: Maximum number of entries to return (default: 100, max: 1000)
    """
    if _game_history is None:
        raise HTTPException(status_code=503, detail="History not initialized")

    if limit and limit > 1000:
        limit = 1000

    return _game_history.get_history(since_tick=since_tick, limit=limit)


@app.post("/player1/command", response_model=TankCommandResponse)
def player1_command(request: TankCommandRequest):
    """Send a command to Player 1 (Blue tank, left side)."""
    if _p1_queue is None:
        raise HTTPException(status_code=503, detail="Player 1 queue not initialized")
    cmd = _validate_command(request.command)
    _p1_queue.put(cmd)
    return TankCommandResponse(status="ok", command=cmd.value, player=1)


@app.post("/player2/command", response_model=TankCommandResponse)
def player2_command(request: TankCommandRequest):
    """Send a command to Player 2 (Red tank, right side). Only available in 2-player mode."""
    if _p2_queue is None:
        raise HTTPException(
            status_code=403,
            detail="Player 2 is AI-controlled in 1-player mode",
        )
    cmd = _validate_command(request.command)
    _p2_queue.put(cmd)
    return TankCommandResponse(status="ok", command=cmd.value, player=2)


@app.post("/player1/strategy", response_model=StrategyResponse)
def player1_strategy(request: StrategyRequest):
    """Send a natural language strategy to Player 1 (Blue tank).

    The game parses the text and executes it tick-by-tick automatically.
    Replaces any previously active strategy. Send "stop" to clear.
    """
    if _p1_queue is None:
        raise HTTPException(status_code=503, detail="Player 1 queue not initialized")
    return _handle_strategy(request.text, _p1_queue, player=1)


@app.post("/player2/strategy", response_model=StrategyResponse)
def player2_strategy(request: StrategyRequest):
    """Send a natural language strategy to Player 2 (Red tank). Only available in 2-player mode."""
    if _p2_queue is None:
        raise HTTPException(
            status_code=403,
            detail="Player 2 is AI-controlled in 1-player mode",
        )
    return _handle_strategy(request.text, _p2_queue, player=2)


def _handle_strategy(text: str, queue: Queue, player: int) -> StrategyResponse:
    text = text.strip()
    if not text or text.lower() == "stop":
        queue.put(("clear_strategy",))
        return StrategyResponse(status="ok", text=text or "stop", parsed=[], player=player)

    parsed = parse_command(text)
    if not parsed:
        raise HTTPException(
            status_code=400,
            detail=f"Could not parse any commands from: '{text}'",
        )
    queue.put(("strategy", text, parsed))
    return StrategyResponse(
        status="ok",
        text=text,
        parsed=[{"type": p.type.name, "params": p.params} for p in parsed],
        player=player,
    )


def run_tank_api(
    p1_queue: Queue,
    p2_queue: Optional[Queue],
    game_state,
    game_history,
    host: str = "0.0.0.0",
    port: int = 8080,
):
    """Start the API server in the calling thread (blocks).

    Args:
        p1_queue: Queue for player 1 commands.
        p2_queue: Queue for player 2 commands (None in 1-player mode).
        game_state: Shared GameState instance.
        game_history: Shared GameHistory instance.
        host: Host to bind to.
        port: Port to listen on.
    """
    global _p1_queue, _p2_queue, _game_state, _game_history
    _p1_queue = p1_queue
    _p2_queue = p2_queue
    _game_state = game_state
    _game_history = game_history

    import uvicorn

    print("\n" + "=" * 60)
    print("Tank Arena API Server")
    print("=" * 60)
    print(f"\nServer running at http://{host}:{port}")
    print("\nEndpoints:")
    print("  GET  /                   - Health check")
    print("  GET  /state              - Full game state")
    print("  GET  /log                - Command & snapshot history")
    print("  POST /player1/command    - Low-level command (Blue tank)")
    print("  POST /player2/command    - Low-level command (Red tank)")
    print("  POST /player1/strategy   - NL strategy (Blue tank)")
    print("  POST /player2/strategy   - NL strategy (Red tank)")
    print("\nLow-level commands: forward, backward, rotate_left, rotate_right, shoot, stop, auto_shoot_on, auto_shoot_off")
    print("\nExamples:")
    print(f'  curl -X POST http://localhost:{port}/player1/command \\')
    print('       -H "Content-Type: application/json" \\')
    print('       -d \'{"command": "forward"}\'')
    print(f'\n  curl -X POST http://localhost:{port}/player1/strategy \\')
    print('       -H "Content-Type: application/json" \\')
    print('       -d \'{"text": "patrol between B2 and B9 and shoot at anything in your sight"}\'')
    print("=" * 60 + "\n")

    uvicorn.run(app, host=host, port=port, log_level="info")
