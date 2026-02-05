"""Grid coordinate helpers and angle utilities for the tank game.

Provides conversion between grid notation (e.g. 'B5') and pixel
coordinates, compass direction mapping, and line-of-sight checks.

Grid layout:
    Columns A-R (0-17), Rows 1-12 (0-11)
    Each cell is CELL_SIZE (50) pixels wide/tall.
    Cell 'A1' has its top-left corner at pixel (0, 0).
"""
import math
from typing import Tuple

from tanks.constants import CELL_SIZE, WINDOW_WIDTH, WINDOW_HEIGHT

# ---- Compass directions mapped to game angles (0=up, CW) ----
COMPASS_ANGLES = {
    "N": 0, "NE": 45, "E": 90, "SE": 135,
    "S": 180, "SW": 225, "W": 270, "NW": 315,
}
COMPASS_ALIASES = {
    "NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W",
    "NORTHEAST": "NE", "NORTHWEST": "NW",
    "SOUTHEAST": "SE", "SOUTHWEST": "SW",
}


def cell_to_pixel(cell: str) -> Tuple[float, float]:
    """Convert grid notation to pixel center coordinates.

    'B5' → column B (index 1), row 5 (index 4) → pixel center (75.0, 225.0).
    """
    cell = cell.strip().upper()
    col = ord(cell[0]) - ord('A')
    row = int(cell[1:]) - 1
    return (col * CELL_SIZE + CELL_SIZE / 2,
            row * CELL_SIZE + CELL_SIZE / 2)


def pixel_to_cell(x: float, y: float) -> str:
    """Convert pixel coordinates to grid notation."""
    col = int(x // CELL_SIZE)
    row = int(y // CELL_SIZE)
    col = max(0, min(col, WINDOW_WIDTH // CELL_SIZE - 1))
    row = max(0, min(row, WINDOW_HEIGHT // CELL_SIZE - 1))
    return f"{chr(ord('A') + col)}{row + 1}"


def angle_to_compass(angle: float) -> str:
    """Convert a game angle (0=up, CW) to nearest 8-direction compass string."""
    angle = angle % 360
    # Each sector spans 45°, centered on the compass direction
    index = int((angle + 22.5) / 45) % 8
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return directions[index]


def resolve_compass(name: str) -> str:
    """Resolve a compass name or alias to a canonical key (N, NE, E, etc.)."""
    name = name.strip().upper()
    if name in COMPASS_ANGLES:
        return name
    return COMPASS_ALIASES.get(name, name)


def angle_to_target(from_x: float, from_y: float,
                    to_x: float, to_y: float) -> float:
    """Angle in game coords (0=up, CW) from source point to target point."""
    dx = to_x - from_x
    dy = to_y - from_y
    return math.degrees(math.atan2(dx, -dy)) % 360


def distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Euclidean distance between two points."""
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def angle_error(desired: float, current: float) -> float:
    """Signed angle difference normalized to [-180, 180].

    Positive means target is to the right (rotate CW).
    """
    return (desired - current + 180) % 360 - 180


def has_clear_los(x1: float, y1: float, x2: float, y2: float,
                  level) -> bool:
    """Check if a straight line between two pixel positions is free of obstacles.

    Uses a DDA grid traversal to walk every cell the ray passes through
    and checks against the level's collision map.
    """
    from tanks.constants import CELL_SIZE

    col1 = int(x1 // CELL_SIZE)
    row1 = int(y1 // CELL_SIZE)
    col2 = int(x2 // CELL_SIZE)
    row2 = int(y2 // CELL_SIZE)

    dc = abs(col2 - col1)
    dr = abs(row2 - row1)
    step_c = 1 if col2 >= col1 else -1
    step_r = 1 if row2 >= row1 else -1

    # Bresenham-style traversal
    error = dc - dr
    c, r = col1, row1
    while True:
        # Skip the starting cell (the shooter's own cell)
        if (c, r) != (col1, row1):
            if not (0 <= c < level.columns and 0 <= r < level.rows):
                break
            if level.collision_map[r][c]:
                return False
        if c == col2 and r == row2:
            break
        e2 = 2 * error
        if e2 > -dr:
            error -= dr
            c += step_c
        if e2 < dc:
            error += dc
            r += step_r

    return True


def is_in_sight(me: dict, target: dict,
                fov: float = 120.0, max_range: float = 800.0,
                level=None) -> bool:
    """Check if *target* is within the FOV cone of *me*.

    Args:
        me: Snapshot dict with keys x, y, angle.
        target: Snapshot dict with keys x, y, alive.
        fov: Total field-of-view angle in degrees (cone is ±fov/2).
        max_range: Maximum detection distance in pixels.
        level: Optional Level object. When provided, obstacles that
            block the line of sight cause this to return False.
    """
    if not target.get("alive", False):
        return False
    dist = distance(me["x"], me["y"], target["x"], target["y"])
    if dist > max_range:
        return False
    desired = angle_to_target(me["x"], me["y"], target["x"], target["y"])
    err = angle_error(desired, me["angle"])
    if abs(err) >= fov / 2:
        return False
    if level is not None:
        return has_clear_los(me["x"], me["y"], target["x"], target["y"], level)
    return True
