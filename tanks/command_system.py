"""High-level command parser and executor for tanks.

Parses natural-language command strings like
    "Patrol between B2 and B9 and shoot at anything in your sight"
into structured commands, then executes them tick-by-tick by emitting
low-level TankCommand enums.

Command classification:
    One-time  — MOVE_TO, FACE, SHOOT_ONCE  (complete when goal reached)
    Repeating — PATROL, GUARD, SHOOT_ON_SIGHT (run until replaced)
"""
import math
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional

from tanks.constants import TankCommand, CELL_SIZE
from tanks.navigation import (
    cell_to_pixel, angle_to_target, angle_error, distance,
    is_in_sight, COMPASS_ANGLES, resolve_compass,
)
from tanks.obstacle_avoidance import ObstacleAvoider


# ---------------------------------------------------------------------------
# Command types
# ---------------------------------------------------------------------------

class CommandType(Enum):
    MOVE_TO = auto()          # one-time: go to grid cell
    FACE = auto()             # one-time: rotate to compass direction
    SHOOT_ONCE = auto()       # one-time: fire one shot
    PATROL = auto()           # repeating: move between two cells
    GUARD = auto()            # repeating: hold position, shoot enemies
    SHOOT_ON_SIGHT = auto()   # repeating modifier: shoot when enemy in FOV


_REPEATING_TYPES = {CommandType.PATROL, CommandType.GUARD, CommandType.SHOOT_ON_SIGHT}
_MOVEMENT_TYPES = {CommandType.MOVE_TO, CommandType.PATROL, CommandType.GUARD}


@dataclass
class ParsedCommand:
    type: CommandType
    params: Dict = field(default_factory=dict)

    @property
    def is_repeating(self) -> bool:
        return self.type in _REPEATING_TYPES

    @property
    def is_movement(self) -> bool:
        return self.type in _MOVEMENT_TYPES


# ---------------------------------------------------------------------------
# Parser — regex-based keyword matching with synonym support
# ---------------------------------------------------------------------------

# Synonym groups for more flexible natural language understanding
_PATROL_VERBS = r"(?:patrol|circle|loop|alternate|go back and forth)"
_MOVE_VERBS = r"(?:move|go|travel|navigate|drive|head|proceed|advance|retreat)"
_GUARD_VERBS = r"(?:guard|defend|hold|protect|secure|camp)"
_FACE_VERBS = r"(?:face|turn|rotate|look|point|aim)"
_SHOOT_VERBS = r"(?:shoot|fire|attack|engage)"

# Prepositions and connectors
_TO_PREP = r"(?:to|towards?|at)"
_BETWEEN_PREP = r"(?:between|from)"
_AND_CONJ = r"(?:and|to)"

# Cell pattern (allows optional "cell" prefix)
_CELL = r"(?:cell\s+)?([A-Ra-r]\d{1,2})"

# Ordered list: first match wins for each category.
_PATTERNS = [
    # PATROL must come before MOVE_TO so "patrol between X and Y" isn't
    # partially eaten by the move pattern.
    # Now supports: "patrol between X and Y", "go back and forth between X and Y",
    # "circle between X and Y", "patrol from X to Y"
    (
        re.compile(
            rf"{_PATROL_VERBS}\s+{_BETWEEN_PREP}\s+{_CELL}\s+{_AND_CONJ}\s+{_CELL}",
            re.IGNORECASE,
        ),
        lambda m: ParsedCommand(
            CommandType.PATROL,
            {"cell_a": m.group(1).upper(), "cell_b": m.group(2).upper()},
        ),
    ),
    # GUARD with more flexible phrasing
    # Supports: "guard E5", "defend position E5", "hold E5", "protect cell E5"
    (
        re.compile(
            rf"{_GUARD_VERBS}\s+(?:(?:position|area|spot|point|the)\s+)?(?:{_TO_PREP}\s+)?{_CELL}",
            re.IGNORECASE,
        ),
        lambda m: ParsedCommand(
            CommandType.GUARD,
            {"cell": m.group(1).upper()},
        ),
    ),
    # MOVE_TO with synonym support
    # Supports: "move to X", "go to X", "navigate to X", "head towards X", "advance to X"
    (
        re.compile(
            rf"{_MOVE_VERBS}\s+{_TO_PREP}\s+{_CELL}",
            re.IGNORECASE,
        ),
        lambda m: ParsedCommand(
            CommandType.MOVE_TO,
            {"cell": m.group(1).upper()},
        ),
    ),
    # FACE with more direction options
    # Supports: "face north", "turn east", "rotate west", "look northeast"
    # Also accepts full words: northeast, northwest, southeast, southwest
    (
        re.compile(
            rf"{_FACE_VERBS}\s+(north(?:east)?|south(?:east)?|east|west|ne|nw|se|sw|[nsew])\b",
            re.IGNORECASE,
        ),
        lambda m: ParsedCommand(
            CommandType.FACE,
            {"direction": resolve_compass(m.group(1))},
        ),
    ),
    # SHOOT_ON_SIGHT with more flexible phrasing
    # Supports: "shoot at anything in sight", "fire at enemies", "attack targets on sight",
    # "engage enemies in view", "shoot on contact"
    (
        re.compile(
            rf"{_SHOOT_VERBS}\s+(?:at\s+)?(?:any(?:thing|one)?|enemies?|targets?|hostiles?|contacts?|opponents?).*?(?:(?:in|on|within)\s+)?(?:your\s+)?(?:sight|view|range|contact)",
            re.IGNORECASE,
        ),
        lambda m: ParsedCommand(CommandType.SHOOT_ON_SIGHT),
    ),
    # Bare shoot command with synonym support
    # Supports: "shoot", "fire", "attack"
    (
        re.compile(rf"\b{_SHOOT_VERBS}\b", re.IGNORECASE),
        lambda m: ParsedCommand(CommandType.SHOOT_ONCE),
    ),
]


def _validate_cell(cell: str) -> bool:
    """Validate that a cell reference is within arena bounds.

    Valid cells: A-R (18 columns) x 1-12 (12 rows).
    Returns True if valid, False otherwise.
    """
    if not cell or len(cell) < 2:
        return False

    col = cell[0].upper()
    try:
        row = int(cell[1:])
    except ValueError:
        return False

    return 'A' <= col <= 'R' and 1 <= row <= 12


def parse_command(text: str) -> List[ParsedCommand]:
    """Parse a natural-language command string into one or more ParsedCommands.

    Supports compound commands joined by 'and':
        "Patrol between B2 and B9 and shoot at anything in your sight"
        → [PATROL(B2, B9), SHOOT_ON_SIGHT]

    The parser greedily matches the longest patterns first, strips them
    from the remaining text, then splits on ' and ' to find additional
    commands.

    Cell coordinates are validated (A-R, 1-12). Invalid commands are
    silently filtered out.
    """
    results: List[ParsedCommand] = []
    remaining = text.strip()

    # Greedily match known patterns
    for regex, builder in _PATTERNS:
        m = regex.search(remaining)
        if m:
            results.append(builder(m))
            # Remove matched span so it doesn't interfere with further parsing
            remaining = remaining[:m.start()] + remaining[m.end():]

    # If nothing matched from the full text, try splitting on ' and '
    # (handles edge cases where the first pass missed fragments).
    if not results:
        for fragment in re.split(r"\s+and\s+", text, flags=re.IGNORECASE):
            fragment = fragment.strip()
            if not fragment:
                continue
            for regex, builder in _PATTERNS:
                m = regex.search(fragment)
                if m:
                    results.append(builder(m))
                    break

    # Validate cell coordinates in parsed commands
    validated_results: List[ParsedCommand] = []
    for cmd in results:
        valid = True
        # Check PATROL cells
        if cmd.type == CommandType.PATROL:
            if not (_validate_cell(cmd.params.get("cell_a", "")) and
                    _validate_cell(cmd.params.get("cell_b", ""))):
                print(f"Warning: Invalid cell coordinates in patrol command: "
                      f"{cmd.params.get('cell_a')} to {cmd.params.get('cell_b')}")
                valid = False
        # Check MOVE_TO and GUARD cells
        elif cmd.type in {CommandType.MOVE_TO, CommandType.GUARD}:
            if not _validate_cell(cmd.params.get("cell", "")):
                print(f"Warning: Invalid cell coordinate: {cmd.params.get('cell')}")
                valid = False

        if valid:
            validated_results.append(cmd)

    return validated_results


# ---------------------------------------------------------------------------
# Command executor — converts parsed commands into TankCommand per tick
# ---------------------------------------------------------------------------

# Tuning constants
_ARRIVE_DIST = 25.0     # pixels — "close enough" to waypoint
_AIM_THRESHOLD = 8.0    # degrees — start moving forward once roughly aimed
_MOVE_ANGLE = 30.0      # degrees — max angle error while still advancing
_SHOOT_AIM = 5.0        # degrees — precision needed to fire (looking right at target)


class CommandExecutor:
    """Holds active commands for a single tank and emits TankCommand lists each tick."""

    def __init__(self, level=None) -> None:
        self.commands: List[ParsedCommand] = []
        self._patrol_idx: int = 0       # which waypoint we're heading toward
        self._completed: set = set()    # indices of completed one-time commands
        self._level = level             # Level for obstacle avoidance (None = disabled)
        self._avoider = ObstacleAvoider() if level is not None else None

    def set_commands(self, commands: List[ParsedCommand]) -> None:
        """Replace all active commands (called at scenario start)."""
        self.commands = list(commands)
        self._patrol_idx = 0
        self._completed = set()

    def tick(self, me: dict, enemy: dict) -> List[TankCommand]:
        """Produce a list of TankCommand enums for this frame.

        Args:
            me: Snapshot dict of this tank (x, y, angle, health, alive).
            enemy: Snapshot dict of the opposing tank.
        """
        if not me.get("alive", False):
            return [TankCommand.STOP]

        # Pre-check: if SHOOT_ON_SIGHT is active and enemy is visible,
        # the tank should prioritise engaging over movement.
        engaging = False
        for cmd in self.commands:
            if cmd.type == CommandType.SHOOT_ON_SIGHT:
                engage_cmds = self._exec_shoot_on_sight(me, enemy)
                if engage_cmds:
                    engaging = True
                break

        result: List[TankCommand] = []
        has_movement = False

        for i, cmd in enumerate(self.commands):
            if i in self._completed:
                continue

            if cmd.type == CommandType.MOVE_TO:
                if not has_movement and not engaging:
                    cmds, done = self._exec_move_to(me, cmd)
                    result.extend(cmds)
                    has_movement = True
                    if done:
                        self._completed.add(i)

            elif cmd.type == CommandType.PATROL:
                if not has_movement and not engaging:
                    result.extend(self._exec_patrol(me, cmd))
                    has_movement = True

            elif cmd.type == CommandType.GUARD:
                if not has_movement and not engaging:
                    result.extend(self._exec_guard(me, enemy, cmd))
                    has_movement = True

            elif cmd.type == CommandType.FACE:
                if not engaging:
                    cmds, done = self._exec_face(me, cmd)
                    result.extend(cmds)
                    if done:
                        self._completed.add(i)

            elif cmd.type == CommandType.SHOOT_ONCE:
                result.append(TankCommand.SHOOT)
                self._completed.add(i)

            elif cmd.type == CommandType.SHOOT_ON_SIGHT:
                result.extend(self._exec_shoot_on_sight(me, enemy))

        return result if result else [TankCommand.STOP]

    # ---- Per-command executors ----

    def _exec_move_to(self, me: dict, cmd: ParsedCommand):
        """Navigate toward a single cell. Returns (commands, is_done)."""
        tx, ty = cell_to_pixel(cmd.params["cell"])
        return self._navigate_toward(me, tx, ty, stop_on_arrive=True)

    def _exec_patrol(self, me: dict, cmd: ParsedCommand) -> List[TankCommand]:
        """Move toward current patrol waypoint; flip on arrival."""
        cells = [cmd.params["cell_a"], cmd.params["cell_b"]]
        target_cell = cells[self._patrol_idx % 2]
        tx, ty = cell_to_pixel(target_cell)

        cmds, arrived = self._navigate_toward(me, tx, ty, stop_on_arrive=False)
        if arrived:
            self._patrol_idx += 1
        return cmds

    def _exec_guard(self, me: dict, enemy: dict,
                    cmd: ParsedCommand) -> List[TankCommand]:
        """Hold a position; shoot enemies that come into view."""
        gx, gy = cell_to_pixel(cmd.params["cell"])
        dist_to_post = distance(me["x"], me["y"], gx, gy)

        # If far from guard position, navigate toward it
        if dist_to_post > _ARRIVE_DIST * 1.6:
            cmds, _ = self._navigate_toward(me, gx, gy, stop_on_arrive=False)
            # Still check for enemies while moving
            if is_in_sight(me, enemy, level=self._level):
                # Aim from bullet spawn position to enemy center mass
                rad = math.radians(me["angle"])
                spawn_dist = CELL_SIZE * 0.45
                bullet_x = me["x"] + math.sin(rad) * spawn_dist
                bullet_y = me["y"] - math.cos(rad) * spawn_dist
                desired = angle_to_target(bullet_x, bullet_y,
                                          enemy["x"], enemy["y"])
                err = angle_error(desired, me["angle"])
                if abs(err) < _SHOOT_AIM:
                    cmds.append(TankCommand.SHOOT)
            return cmds

        # At guard post — scan for enemy
        if enemy.get("alive") and is_in_sight(me, enemy, level=self._level):
            # Aim from bullet spawn position to enemy center mass
            rad = math.radians(me["angle"])
            spawn_dist = CELL_SIZE * 0.45
            bullet_x = me["x"] + math.sin(rad) * spawn_dist
            bullet_y = me["y"] - math.cos(rad) * spawn_dist
            desired = angle_to_target(bullet_x, bullet_y,
                                      enemy["x"], enemy["y"])
            err = angle_error(desired, me["angle"])
            cmds: List[TankCommand] = []
            if abs(err) > _AIM_THRESHOLD:
                cmds.append(
                    TankCommand.ROTATE_RIGHT if err > 0
                    else TankCommand.ROTATE_LEFT
                )
            if abs(err) < _SHOOT_AIM:
                cmds.append(TankCommand.SHOOT)
            return cmds if cmds else [TankCommand.STOP]

        return [TankCommand.STOP]

    def _exec_face(self, me: dict, cmd: ParsedCommand):
        """Rotate to face a compass direction. Returns (commands, is_done)."""
        direction = cmd.params["direction"]
        target_angle = COMPASS_ANGLES.get(direction, 0)
        err = angle_error(target_angle, me["angle"])
        if abs(err) < 5.0:
            return ([TankCommand.STOP], True)
        cmd_rot = TankCommand.ROTATE_RIGHT if err > 0 else TankCommand.ROTATE_LEFT
        return ([cmd_rot], False)

    def _exec_shoot_on_sight(self, me: dict, enemy: dict) -> List[TankCommand]:
        """Turn toward and fire at enemy when within the FOV cone.

        While engaging, the tank also creeps forward (at shoot-slowdown
        speed) so it doesn't freeze in place.
        """
        if not is_in_sight(me, enemy, level=self._level):
            return []

        # Calculate aim angle from bullet spawn position to enemy center mass
        # This accounts for the 45-pixel barrel offset and ensures accurate center-mass targeting
        rad = math.radians(me["angle"])
        spawn_dist = CELL_SIZE * 0.45
        bullet_x = me["x"] + math.sin(rad) * spawn_dist
        bullet_y = me["y"] - math.cos(rad) * spawn_dist
        desired = angle_to_target(bullet_x, bullet_y, enemy["x"], enemy["y"])

        err = angle_error(desired, me["angle"])
        cmds: List[TankCommand] = []
        if abs(err) > _AIM_THRESHOLD:
            cmds.append(
                TankCommand.ROTATE_RIGHT if err > 0
                else TankCommand.ROTATE_LEFT
            )
        if abs(err) < _SHOOT_AIM:
            cmds.append(TankCommand.SHOOT)
        # Keep moving forward while engaging (shoot slowdown handles speed)
        cmds.append(TankCommand.FORWARD)
        return cmds

    # ---- Shared navigation helper ----

    def _navigate_toward(self, me: dict, tx: float, ty: float,
                         stop_on_arrive: bool):
        """Steer toward (tx, ty). Returns (commands, arrived_bool)."""
        dist = distance(me["x"], me["y"], tx, ty)
        if dist <= _ARRIVE_DIST:
            if stop_on_arrive:
                return ([TankCommand.STOP], True)
            return ([], True)

        # Obstacle avoidance: if a level is available, check for obstacles
        # ahead and steer around them before falling back to normal aiming.
        if self._avoider is not None:
            avoidance = self._avoider(
                me["x"], me["y"], me["angle"], self._level, tx, ty,
            )
            if avoidance is not None:
                return (avoidance, False)

        desired = angle_to_target(me["x"], me["y"], tx, ty)
        err = angle_error(desired, me["angle"])

        cmds: List[TankCommand] = []
        if abs(err) > _AIM_THRESHOLD:
            cmds.append(
                TankCommand.ROTATE_RIGHT if err > 0
                else TankCommand.ROTATE_LEFT
            )
        if abs(err) < _MOVE_ANGLE:
            cmds.append(TankCommand.FORWARD)
        return (cmds, False)
