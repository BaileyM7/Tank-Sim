"""Obstacle avoidance system for AI and API-controlled tanks.

Implements a sensor ring -- an invisible detection zone projected ahead
of the tank that senses upcoming obstacles and generates steering
corrections to navigate around them automatically.

Algorithm:
    1. Project the tank's hitbox forward along its current heading at
       several sample distances (up to SENSE_RADIUS pixels).
    2. If the projected hitbox overlaps a blocked cell, the path is
       considered obstructed.
    3. Probe alternate directions (left and right at increasing angles)
       to find the clearest side.
    4. Emit rotation commands toward the clear side, optionally still
       moving forward if the obstacle is far enough away.
    5. When a navigation target is provided, ties are broken by
       preferring the side that faces the target.

Direction commitment (hysteresis):
    Once a steering direction is chosen, the avoider *commits* to it
    until the obstacle is cleared or the opposite side becomes
    significantly clearer (2+ probe advantage).  This prevents the
    jittery left-right oscillation that occurs when approaching an
    obstacle nearly head-on.

Applies to:
    - AI controller  (1-player mode opponent)
    - API / command-system controlled tanks
    - Demo mode tanks

Does NOT apply to:
    - Manual keyboard control
"""

import math
from typing import List, Optional

from tanks.constants import CELL_SIZE, TANK_HITBOX_HALF, TankCommand

# ---------------------------------------------------------------------------
# Tuning constants
# ---------------------------------------------------------------------------

SENSE_RADIUS = 170.0      # How far ahead the sensor ring extends (pixels)
INNER_RADIUS = 100.0      # Close-range threshold -- no forward if closer
PROBE_STEPS = 5           # Sample points per feeler ray
SIDE_ANGLES = [30, 60, 90]  # Offsets (degrees) for clearance probes
HYSTERESIS = 2            # Side must be this many probes clearer to override


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _probe_direction(x: float, y: float, angle_deg: float, level,
                     radius: float = SENSE_RADIUS,
                     steps: int = PROBE_STEPS):
    """Project the tank hitbox forward along *angle_deg* and detect collision.

    Returns ``(blocked, distance_to_first_block)``.  *distance* equals
    *radius* when the path is completely clear.
    """
    rad = math.radians(angle_deg)
    dx = math.sin(rad)
    dy = -math.cos(rad)
    h = TANK_HITBOX_HALF
    step_size = radius / steps

    for i in range(1, steps + 1):
        px = x + dx * step_size * i
        py = y + dy * step_size * i
        # Check all four corners of the hitbox at the projected position
        for cx, cy in [(px - h, py - h), (px + h, py - h),
                       (px - h, py + h), (px + h, py + h)]:
            col = int(cx // CELL_SIZE)
            row = int(cy // CELL_SIZE)
            if not level.is_passable(col, row):
                return (True, step_size * i)

    return (False, radius)


def _survey_sides(x: float, y: float, angle: float, level):
    """Count how many side probes are clear on each side."""
    left_clear = 0
    right_clear = 0
    for offset in SIDE_ANGLES:
        l_blocked, _ = _probe_direction(x, y, (angle - offset) % 360, level)
        r_blocked, _ = _probe_direction(x, y, (angle + offset) % 360, level)
        if not l_blocked:
            left_clear += 1
        if not r_blocked:
            right_clear += 1
    return left_clear, right_clear


def _pick_direction(left_clear: int, right_clear: int,
                    x: float, y: float, angle: float,
                    target_x: float = None,
                    target_y: float = None) -> TankCommand:
    """Choose a rotation direction from scratch (no prior commitment)."""
    if left_clear > right_clear:
        return TankCommand.ROTATE_LEFT
    if right_clear > left_clear:
        return TankCommand.ROTATE_RIGHT
    # Tie -- break toward navigation target if available.
    if target_x is not None and target_y is not None:
        target_angle = math.degrees(
            math.atan2(target_x - x, -(target_y - y))
        ) % 360
        err = (target_angle - angle + 180) % 360 - 180
        return TankCommand.ROTATE_RIGHT if err >= 0 else TankCommand.ROTATE_LEFT
    return TankCommand.ROTATE_LEFT  # final fallback


# ---------------------------------------------------------------------------
# Public API — stateful avoider (preferred)
# ---------------------------------------------------------------------------

class ObstacleAvoider:
    """Stateful obstacle avoider that commits to a direction.

    Create one instance per tank.  Call it every tick; it remembers
    which direction it last chose and only switches when the opposite
    side is significantly clearer (``HYSTERESIS`` probe advantage).

    A *grace period* prevents jitter at obstacle boundaries: after the
    center probe clears, the avoider keeps steering in the committed
    direction for ``CLEAR_GRACE`` extra frames so the tank fully clears
    the obstacle edge before resuming normal navigation.

    Usage::

        avoider = ObstacleAvoider()
        cmds = avoider(x, y, angle, level, target_x, target_y)
        if cmds is None:
            # path clear, navigate normally
    """

    CLEAR_GRACE = 6  # frames to keep committed direction after path clears

    def __init__(self) -> None:
        self._committed: Optional[TankCommand] = None
        self._clear_frames: int = 0

    def reset(self) -> None:
        """Clear the committed direction (e.g. on respawn)."""
        self._committed = None
        self._clear_frames = 0

    def __call__(self, x: float, y: float, angle: float, level,
                 target_x: float = None,
                 target_y: float = None) -> Optional[List[TankCommand]]:
        """Sense obstacles and return avoidance commands.

        Returns ``None`` when the path ahead is clear.
        """
        center_blocked, center_dist = _probe_direction(x, y, angle, level)

        if not center_blocked:
            if self._committed is not None:
                # Path just cleared — keep rotating for a grace period so
                # the tank doesn't immediately turn back into the obstacle.
                self._clear_frames += 1
                if self._clear_frames >= self.CLEAR_GRACE:
                    self._committed = None
                    self._clear_frames = 0
                    return None
                # Grace period: keep steering away, but allow forward
                # movement since the immediate path is clear.
                return [self._committed, TankCommand.FORWARD]
            return None

        # Path blocked — reset the clear-frame counter.
        self._clear_frames = 0

        left_clear, right_clear = _survey_sides(x, y, angle, level)

        # --- direction selection with hysteresis ---
        if self._committed is not None:
            # Already committed — only switch if the other side is
            # clearly better (HYSTERESIS advantage).
            if self._committed == TankCommand.ROTATE_LEFT:
                if right_clear >= left_clear + HYSTERESIS:
                    self._committed = TankCommand.ROTATE_RIGHT
            else:
                if left_clear >= right_clear + HYSTERESIS:
                    self._committed = TankCommand.ROTATE_LEFT
        else:
            # First encounter — pick the best side.
            self._committed = _pick_direction(
                left_clear, right_clear, x, y, angle, target_x, target_y,
            )

        cmds: List[TankCommand] = [self._committed]
        if center_dist > INNER_RADIUS:
            cmds.append(TankCommand.FORWARD)
        return cmds


# ---------------------------------------------------------------------------
# Public API — stateless function (kept for simple one-off checks)
# ---------------------------------------------------------------------------

def avoid_obstacles(x: float, y: float, angle: float, level,
                    target_x: float = None,
                    target_y: float = None) -> Optional[List[TankCommand]]:
    """Stateless version — no direction commitment.

    Prefer ``ObstacleAvoider`` for per-tank usage to prevent jitter.
    This function is still useful for single-frame checks where no
    persistent state is available.
    """
    center_blocked, center_dist = _probe_direction(x, y, angle, level)
    if not center_blocked:
        return None

    left_clear, right_clear = _survey_sides(x, y, angle, level)
    direction = _pick_direction(
        left_clear, right_clear, x, y, angle, target_x, target_y,
    )

    cmds: List[TankCommand] = [direction]
    if center_dist > INNER_RADIUS:
        cmds.append(TankCommand.FORWARD)
    return cmds
