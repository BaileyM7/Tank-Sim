from enum import Enum
from pathlib import Path

# ---- Window & Grid ----
WINDOW_WIDTH = 1800
WINDOW_HEIGHT = 1200
CELL_SIZE = 100
GRID_COLS = WINDOW_WIDTH // CELL_SIZE   # 18
GRID_ROWS = WINDOW_HEIGHT // CELL_SIZE  # 12
WINDOW_TITLE = "Tank Arena"
FPS = 30

# ---- Paths ----
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSET_ROOT = PROJECT_ROOT / "Kenney_topdownTanks" / "PNG"
LEVELS_DIR = Path(__file__).resolve().parent / "levels"

ENVIRONMENT_DIR = ASSET_ROOT / "Environment"
OBSTACLES_DIR = ASSET_ROOT / "Obstacles"
TANKS_DIR = ASSET_ROOT / "Tanks"
BULLETS_DIR = ASSET_ROOT / "Bullets"


# ---- Terrain Types ----
class TerrainType(Enum):
    GRASS = "grass"
    DIRT = "dirt"
    SAND = "sand"


TERRAIN_FILES = {
    TerrainType.GRASS: "grass.png",
    TerrainType.DIRT: "dirt.png",
    TerrainType.SAND: "sand.png",
}


# ---- Obstacle Types ----
class ObstacleType(Enum):
    BARREL_GREEN = "barrel_green"
    BARREL_GREY = "barrel_grey"
    BARREL_RED = "barrel_red"
    SANDBAG_BEIGE = "sandbag_beige"
    SANDBAG_BROWN = "sandbag_brown"
    TREE_LARGE = "tree_large"
    TREE_SMALL = "tree_small"
    OIL = "oil"


# Maps ObstacleType -> (directory, filename, default_span_cols, default_span_rows)
OBSTACLE_DEFS = {
    ObstacleType.BARREL_GREEN:  (OBSTACLES_DIR,    "barrelGreen_up.png",  1, 1),
    ObstacleType.BARREL_GREY:   (OBSTACLES_DIR,    "barrelGrey_up.png",   1, 1),
    ObstacleType.BARREL_RED:    (OBSTACLES_DIR,    "barrelRed_up.png",    1, 1),
    ObstacleType.SANDBAG_BEIGE: (OBSTACLES_DIR,    "sandbagBeige.png",    1, 1),
    ObstacleType.SANDBAG_BROWN: (OBSTACLES_DIR,    "sandbagBrown.png",    1, 1),
    ObstacleType.TREE_LARGE:    (ENVIRONMENT_DIR,  "treeLarge.png",       2, 2),
    ObstacleType.TREE_SMALL:    (ENVIRONMENT_DIR,  "treeSmall.png",       1, 1),
    ObstacleType.OIL:           (OBSTACLES_DIR,    "oil.png",             2, 2),
}

# Whether an obstacle blocks tank movement
OBSTACLE_BLOCKS = {
    ObstacleType.BARREL_GREEN:  True,
    ObstacleType.BARREL_GREY:   True,
    ObstacleType.BARREL_RED:    True,
    ObstacleType.SANDBAG_BEIGE: True,
    ObstacleType.SANDBAG_BROWN: True,
    ObstacleType.TREE_LARGE:    True,
    ObstacleType.TREE_SMALL:    True,
    ObstacleType.OIL:           False,  # Passable (cosmetic/hazard)
}


# ---- Facing Directions ----
class Facing(Enum):
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"


FACING_ANGLES = {
    Facing.UP: 0,
    Facing.RIGHT: -90,
    Facing.DOWN: 180,
    Facing.LEFT: 90,
}


# ---- Tank Colors ----
PLAYER_TANK_COLORS = {
    1: "Blue",
    2: "Red",
}

# ---- Tank Physics ----
TANK_SPEED = 6.0          # pixels per frame
TANK_ROTATION_SPEED = 3.0 # degrees per frame
TANK_HITBOX_HALF = 36     # half-width of square collision box

# ---- Bullet Physics ----
BULLET_SPEED = 20.0
BULLET_COOLDOWN_MS = 400  # ms between shots
SHOOT_SLOWDOWN_MS = 300   # ms of reduced speed after firing
SHOOT_SPEED_FACTOR = 0.5  # speed multiplier while slowed

# ---- Facing -> tank angle (0=up, 90=right, 180=down, 270=left) ----
FACING_TO_ANGLE = {
    Facing.UP: 0,
    Facing.RIGHT: 90,
    Facing.DOWN: 180,
    Facing.LEFT: 270,
}


# ---- Health & Damage ----
TANK_MAX_HEALTH = 3
BULLET_DAMAGE = 1


# ---- Game Phases ----
class GamePhase(Enum):
    TITLE_SCREEN = "title_screen"
    PLAYING = "playing"
    GAME_OVER = "game_over"


# ---- Game Modes ----
class GameMode(Enum):
    ONE_PLAYER = "1p"
    TWO_PLAYER = "2p"
    DEMO = "demo"
    MANUAL = "manual"


# ---- Tank Commands (for API control) ----
class TankCommand(Enum):
    FORWARD = "forward"
    BACKWARD = "backward"
    ROTATE_LEFT = "rotate_left"
    ROTATE_RIGHT = "rotate_right"
    SHOOT = "shoot"
    STOP = "stop"
    AUTO_SHOOT_ON = "auto_shoot_on"
    AUTO_SHOOT_OFF = "auto_shoot_off"


# ---- API Server ----
API_HOST = "0.0.0.0"
API_PORT = 8080
