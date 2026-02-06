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
from fastapi.responses import HTMLResponse
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
    """Health check endpoint with game status."""
    game_active = _p1_queue is not None
    player2_available = _p2_queue is not None

    return {
        "status": "ok",
        "message": "Tank Arena API is running",
        "game_active": game_active,
        "player1_available": game_active,
        "player2_available": player2_available,
        "hint": "Visit /play to play in browser, or /docs for API documentation"
    }


@app.get("/play", response_class=HTMLResponse)
def play_game():
    """Serve the web-based game interface."""
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Tank Arena - Web Play</title>
    <style>
        body {
            margin: 0;
            padding: 20px;
            background: #2a2a2a;
            color: #fff;
            font-family: 'Courier New', monospace;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        h1 { color: #ffd700; }
        #game-container {
            position: relative;
            margin: 20px 0;
        }
        canvas {
            border: 3px solid #444;
            background: #1a1a1a;
        }
        #info {
            width: 1800px;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-top: 20px;
        }
        .player-info {
            background: #333;
            padding: 15px;
            border-radius: 5px;
        }
        .player-info h3 {
            margin-top: 0;
        }
        .blue { color: #6ac3ff; }
        .red { color: #ff6a6a; }
        #controls {
            margin-top: 20px;
            background: #333;
            padding: 15px;
            border-radius: 5px;
            width: 1800px;
        }
        .status {
            margin-top: 10px;
            padding: 10px;
            background: #222;
            border-radius: 3px;
        }
    </style>
</head>
<body>
    <h1>🎮 Tank Arena - Web Interface</h1>

    <div id="game-container">
        <canvas id="gameCanvas" width="1800" height="1200"></canvas>
    </div>

    <div id="info">
        <div class="player-info">
            <h3 class="blue">Blue Tank (You)</h3>
            <div id="p1-info">Position: N/A<br>Health: N/A<br>Angle: N/A</div>
        </div>
        <div class="player-info">
            <h3 class="red">Red Tank (Opponent)</h3>
            <div id="p2-info">Position: N/A<br>Health: N/A<br>Angle: N/A</div>
        </div>
    </div>

    <div id="controls">
        <h3>Controls</h3>
        <p><strong>WASD</strong> - Move • <strong>SPACE</strong> - Shoot • <strong>ESC</strong> - Stop</p>
        <div class="status" id="status">Connecting to game...</div>
    </div>

    <script>
        const canvas = document.getElementById('gameCanvas');
        const ctx = canvas.getContext('2d');
        const CELL_SIZE = 100;

        let gameState = null;
        let lastCommand = null;
        let keysPressed = new Set();

        // Fetch game state
        async function fetchGameState() {
            try {
                const response = await fetch('/state');
                if (response.ok) {
                    gameState = await response.json();
                    render();
                    updateInfo();
                    document.getElementById('status').textContent =
                        `Game Active - Tick: ${gameState.tick} - Phase: ${gameState.phase}`;
                } else {
                    document.getElementById('status').textContent = 'No active game. Start a game from the desktop app.';
                }
            } catch (error) {
                document.getElementById('status').textContent = 'Error connecting to game server.';
            }
        }

        // Send command to API
        async function sendCommand(command) {
            if (command === lastCommand) return; // Don't send duplicate commands
            lastCommand = command;

            try {
                await fetch('/player1/command', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ command })
                });
            } catch (error) {
                console.error('Failed to send command:', error);
            }
        }

        // Keyboard controls
        document.addEventListener('keydown', (e) => {
            keysPressed.add(e.key.toLowerCase());

            // Send command based on key priority
            if (keysPressed.has('w')) sendCommand('forward');
            else if (keysPressed.has('s')) sendCommand('backward');
            else if (keysPressed.has('a')) sendCommand('rotate_left');
            else if (keysPressed.has('d')) sendCommand('rotate_right');
            else if (e.key === ' ') sendCommand('shoot');
        });

        document.addEventListener('keyup', (e) => {
            keysPressed.delete(e.key.toLowerCase());

            // Update command based on remaining keys
            if (keysPressed.size === 0) {
                lastCommand = null; // Reset so next press sends command
            }
        });

        // Render game state
        function render() {
            if (!gameState) return;

            // Clear canvas
            ctx.fillStyle = '#1a1a1a';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            // Draw grid
            ctx.strokeStyle = '#333';
            ctx.lineWidth = 1;
            for (let x = 0; x <= 1800; x += CELL_SIZE) {
                ctx.beginPath();
                ctx.moveTo(x, 0);
                ctx.lineTo(x, 1200);
                ctx.stroke();
            }
            for (let y = 0; y <= 1200; y += CELL_SIZE) {
                ctx.beginPath();
                ctx.moveTo(0, y);
                ctx.lineTo(1800, y);
                ctx.stroke();
            }

            // Draw tanks
            if (gameState.tanks) {
                drawTank(gameState.tanks.player1, '#6ac3ff');
                drawTank(gameState.tanks.player2, '#ff6a6a');
            }
        }

        function drawTank(tank, color) {
            if (!tank || !tank.alive) return;

            const x = tank.x;
            const y = tank.y;
            const angle = tank.angle * Math.PI / 180;

            ctx.save();
            ctx.translate(x, y);
            ctx.rotate(angle);

            // Draw tank body
            ctx.fillStyle = color;
            ctx.fillRect(-25, -25, 50, 50);

            // Draw barrel
            ctx.fillStyle = color;
            ctx.fillRect(-5, -35, 10, 25);

            // Draw health bar
            ctx.restore();
            ctx.fillStyle = '#444';
            ctx.fillRect(x - 40, y - 45, 80, 8);
            ctx.fillStyle = tank.health > 1 ? '#0f0' : '#f00';
            ctx.fillRect(x - 40, y - 45, 80 * (tank.health / 3), 8);

            ctx.restore();
        }

        function updateInfo() {
            if (!gameState || !gameState.tanks) return;

            const p1 = gameState.tanks.player1;
            const p2 = gameState.tanks.player2;

            if (p1) {
                const col = String.fromCharCode(65 + Math.floor(p1.x / CELL_SIZE));
                const row = Math.floor(p1.y / CELL_SIZE) + 1;
                document.getElementById('p1-info').innerHTML =
                    `Position: ${col}${row}<br>Health: ${p1.health}/3<br>Angle: ${Math.round(p1.angle)}°`;
            }

            if (p2) {
                const col = String.fromCharCode(65 + Math.floor(p2.x / CELL_SIZE));
                const row = Math.floor(p2.y / CELL_SIZE) + 1;
                document.getElementById('p2-info').innerHTML =
                    `Position: ${col}${row}<br>Health: ${p2.health}/3<br>Angle: ${Math.round(p2.angle)}°`;
            }
        }

        // Update game state every 33ms (30 FPS)
        setInterval(fetchGameState, 33);

        // Initial fetch
        fetchGameState();
    </script>
</body>
</html>
    """


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
        raise HTTPException(
            status_code=503,
            detail="No active game. Start a game from the title screen (1P or 2P mode) to enable API control."
        )
    cmd = _validate_command(request.command)
    _p1_queue.put(cmd)
    return TankCommandResponse(status="ok", command=cmd.value, player=1)


@app.post("/player2/command", response_model=TankCommandResponse)
def player2_command(request: TankCommandRequest):
    """Send a command to Player 2 (Red tank, right side). Only available in 2-player mode."""
    if _p2_queue is None:
        raise HTTPException(
            status_code=403,
            detail="Player 2 not available. Either no game is active, or Player 2 is AI-controlled in 1-player mode."
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
        raise HTTPException(
            status_code=503,
            detail="No active game. Start a game from the title screen (1P or 2P mode) to enable API control."
        )
    return _handle_strategy(request.text, _p1_queue, player=1)


@app.post("/player2/strategy", response_model=StrategyResponse)
def player2_strategy(request: StrategyRequest):
    """Send a natural language strategy to Player 2 (Red tank). Only available in 2-player mode."""
    if _p2_queue is None:
        raise HTTPException(
            status_code=403,
            detail="Player 2 not available. Either no game is active, or Player 2 is AI-controlled in 1-player mode."
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

    print("\n" + "=" * 70)
    print("Tank Arena API Server")
    print("=" * 70)
    print(f"\nServer running at http://{host}:{port}")
    print(f"Interactive docs: http://localhost:{port}/docs")
    print(f"Alternative docs: http://localhost:{port}/redoc")

    if p1_queue is None and p2_queue is None:
        print("\n[!] Note: API is running but no game is active.")
        print("    Start a game from the title screen to enable tank control.")

    print("\nEndpoints:")
    print("  GET  /                   - Health check")
    print("  GET  /play               - Play game in your browser!")
    print("  GET  /docs               - Interactive API documentation")
    print("  GET  /state              - Full game state")
    print("  GET  /log                - Command & snapshot history")
    print("  POST /player1/command    - Low-level command (Blue tank)")
    print("  POST /player2/command    - Low-level command (Red tank)")
    print("  POST /player1/strategy   - NL strategy (Blue tank)")
    print("  POST /player2/strategy   - NL strategy (Red tank)")
    print("\nLow-level commands: forward, backward, rotate_left, rotate_right,")
    print("                   shoot, stop, auto_shoot_on, auto_shoot_off")
    print("\nExamples:")
    print(f'  curl -X POST http://localhost:{port}/player1/command \\')
    print('       -H "Content-Type: application/json" \\')
    print('       -d \'{"command": "forward"}\'')
    print(f'\n  curl -X POST http://localhost:{port}/player1/strategy \\')
    print('       -H "Content-Type: application/json" \\')
    print('       -d \'{"text": "patrol between B2 and B9 and shoot at anything in your sight"}\'')
    print("=" * 70 + "\n")

    uvicorn.run(app, host=host, port=port, log_level="info")
