# Tanks Game

A top-down tank battle game built with Pygame, featuring AI-controlled opponents and natural language command processing.

## Features

- **Single Player and Two Player Modes**: Play against AI or control both tanks
- **Natural Language Commands**: Control tanks using text commands via API
- **AI Controller**: Smart AI that can navigate, avoid obstacles, and engage targets
- **Level System**: JSON-based level format with walls, obstacles, and spawn points
- **Command System**: Rich command syntax for movement, turning, and shooting
- **Manual Mode**: Direct keyboard control for testing and demos

## Installation

1. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Default Mode (API-based gameplay)
```bash
python -m tanks
```

This launches the game with the title screen where you can select:
- **1 Player**: You control one tank via API, AI controls the other
- **2 Player**: Both tanks controlled via API

### Manual Mode (Keyboard control)
```bash
python -m tanks --manual
```

**Keyboard Controls:**
- W/S - Forward / Backward
- A/D - Rotate Left / Right
- Space - Shoot
- G - Toggle grid overlay
- C - Toggle collision map overlay
- ESC - Quit

## API Control

When running in API mode, the game starts a FastAPI server on port 8001. You can send commands to control the tanks:

```python
import requests

# Get game state
response = requests.get("http://localhost:8001/state")

# Send command to tank 1
requests.post("http://localhost:8001/command/1", json={"command": "move forward 100"})

# Send command to tank 2
requests.post("http://localhost:8001/command/2", json={"command": "turn right 90 then shoot"})
```

### Command Examples
- `move forward 200` - Move forward 200 pixels
- `turn left 45` - Turn left 45 degrees
- `turn right 90 then shoot` - Turn right 90 degrees, then fire
- `shoot` - Fire immediately
- `move backward 100 then turn around` - Move back, then turn 180 degrees

## Project Structure

- `__main__.py` - Main game loop and entry point
- `tank.py` - Tank entity and bullet collision logic
- `level.py` - Level loading and grid representation
- `renderer.py` - Pygame rendering system
- `ai_controller.py` - AI opponent logic
- `command_system.py` - Natural language command parser and executor
- `navigation.py` - Navigation utilities (distance, angles, line of sight)
- `obstacle_avoidance.py` - Collision detection and avoidance
- `tank_api.py` - FastAPI server for external control
- `game_state.py` - Shared game state management
- `game_history.py` - Game event tracking and history
- `assets.py` - Asset loading and management
- `constants.py` - Game constants and enums

## Levels

Levels are stored as JSON files in the `levels/` directory. Each level defines:
- Grid dimensions
- Wall positions
- Obstacle positions
- Tank spawn points

## Requirements

- Python 3.12+
- pygame 2.5+
- FastAPI 0.109+
- uvicorn 0.27+

## License

MIT License
