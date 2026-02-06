"""AI controller for the Red tank in 1-player mode.

Runs on a background daemon thread. Reads game_state snapshots and
uses the same strategy/command system available to players through the API.

The AI generates randomized aggressive strategies that pursue and attack
player 1, using commands like patrol, guard, and shoot on sight.
"""
import math
import random
import time
from queue import Queue
from typing import List, Tuple

from tanks.constants import WINDOW_WIDTH, WINDOW_HEIGHT, CELL_SIZE, TankCommand
from tanks.command_system import CommandExecutor, parse_command, CommandType
from tanks.navigation import distance, angle_to_target, angle_error, is_in_sight


def _pixel_to_cell(x: float, y: float) -> str:
    """Convert pixel coordinates to cell notation (e.g., 'E5')."""
    col = int(x // CELL_SIZE)
    row = int(y // CELL_SIZE)
    # Clamp to valid range: A-R (0-17), 1-12 (0-11)
    col = max(0, min(17, col))
    row = max(0, min(11, row))
    return f"{chr(ord('A') + col)}{row + 1}"


def _get_cells_near_position(x: float, y: float, radius_cells: int = 2) -> List[str]:
    """Get a list of cells near a position within a radius."""
    center_cell = _pixel_to_cell(x, y)
    col_char = center_cell[0]
    row_num = int(center_cell[1:])

    cells = []
    for dc in range(-radius_cells, radius_cells + 1):
        for dr in range(-radius_cells, radius_cells + 1):
            if dc == 0 and dr == 0:
                continue
            new_col = ord(col_char) + dc
            new_row = row_num + dr
            if ord('A') <= new_col <= ord('R') and 1 <= new_row <= 12:
                cells.append(f"{chr(new_col)}{new_row}")
    return cells


# No custom executor - using standard CommandExecutor like demo mode


class AIController:
    """Strategy-based AI opponent.

    Uses the same CommandExecutor system that players use via the API.
    Generates randomized aggressive strategies that pursue player 1.

    Args:
        command_queue: Queue to write strategy tuples into.
        game_state: Shared GameState instance (read-only via snapshot()).
        my_color: Color of the AI-controlled tank.
    """

    TICK_INTERVAL = 1 / 30  # 30 Hz -- match game FPS for smooth movement
    STRATEGY_CHANGE_MIN = 4.0  # Minimum seconds before changing strategy
    STRATEGY_CHANGE_MAX = 10.0  # Maximum seconds before changing strategy
    STARTUP_DELAY = 5.0  # Seconds to wait before AI starts moving (gives player time)

    def __init__(self, command_queue: Queue, game_state,
                 my_color: str = "Red", level=None):
        self.queue = command_queue
        self.game_state = game_state
        self.my_color = my_color
        self.level = level
        self._running = False
        self._executor = None
        self._strategy_start_time = 0
        self._current_strategy_duration = 0
        self._last_enemy_pos = None
        self._game_start_time = None  # Track when game starts for startup delay

    def start(self):
        """Begin the AI loop. Call from a daemon thread."""
        self._running = True
        self._game_start_time = None  # Reset startup timer for new game
        self._run_loop()

    def stop(self):
        """Signal the AI loop to stop."""
        self._running = False
        self._game_start_time = None  # Reset for next game

    def _run_loop(self):
        while self._running:
            snap = self.game_state.snapshot()

            # Wait until actually playing
            if snap["phase"] != "playing":
                time.sleep(0.5)
                continue

            me = snap["tanks"].get("player2")
            enemy = snap["tanks"].get("player1")
            if me is None or enemy is None or not me["alive"]:
                time.sleep(0.2)
                continue

            current_time = time.time()

            # Initialize game start time on first tick
            if self._game_start_time is None:
                self._game_start_time = current_time
                # print("AI: Waiting 3 seconds before engaging...")

            # Startup delay - give player time to get their bearings
            if current_time - self._game_start_time < self.STARTUP_DELAY:
                # AI is idle during startup delay
                time.sleep(self.TICK_INTERVAL)
                continue

            # Check if we need a new strategy
            if (self._executor is None or
                current_time - self._strategy_start_time >= self._current_strategy_duration):
                self._generate_new_strategy(me, enemy)
                self._strategy_start_time = current_time
                # Randomize next strategy change time
                self._current_strategy_duration = random.uniform(
                    self.STRATEGY_CHANGE_MIN,
                    self.STRATEGY_CHANGE_MAX
                )

            # Execute current strategy
            if self._executor and enemy.get("alive"):
                commands = self._executor.tick(me, enemy)
                for cmd in commands:
                    self.queue.put(cmd)

            time.sleep(self.TICK_INTERVAL)

    def _generate_new_strategy(self, me: dict, enemy: dict):
        """Generate a new aggressive strategy focused on pursuing player 1."""
        # Track enemy position for smarter strategies
        self._last_enemy_pos = (enemy["x"], enemy["y"])

        # Get enemy's cell and nearby cells
        enemy_cell = _pixel_to_cell(enemy["x"], enemy["y"])
        my_cell = _pixel_to_cell(me["x"], me["y"])

        # Calculate distance to enemy
        dist = distance(me["x"], me["y"], enemy["x"], enemy["y"])

        # Choose strategy type based on distance and randomization
        strategy_roll = random.random()

        if dist < 200:
            # Close range: aggressive assault or guard nearby
            if strategy_roll < 0.6:
                strategy_text = self._generate_assault_strategy(enemy_cell)
            else:
                strategy_text = self._generate_guard_near_enemy_strategy(enemy_cell)
        elif dist < 400:
            # Medium range: patrol to intercept or direct approach
            if strategy_roll < 0.5:
                strategy_text = self._generate_intercept_patrol_strategy(my_cell, enemy_cell)
            else:
                strategy_text = self._generate_assault_strategy(enemy_cell)
        else:
            # Long range: patrol toward enemy or direct approach
            if strategy_roll < 0.4:
                strategy_text = self._generate_approach_patrol_strategy(my_cell, enemy_cell)
            else:
                strategy_text = self._generate_assault_strategy(enemy_cell)

        # Parse and set the new strategy
        parsed_commands = parse_command(strategy_text)
        if parsed_commands:
            self._executor = CommandExecutor(level=self.level)
            self._executor.set_commands(parsed_commands)
            # Debug output
            # cmd_types = [f"{cmd.type.name}" for cmd in parsed_commands]
            # print(f"AI Strategy: {strategy_text}")
            # print(f"  Parsed commands: {cmd_types}")

    def _generate_assault_strategy(self, enemy_cell: str) -> str:
        """Generate a direct assault strategy toward enemy position."""
        # Get cells near the enemy
        nearby_cells = _get_cells_near_position(
            *self._last_enemy_pos if self._last_enemy_pos else (0, 0),
            radius_cells=3
        )

        if nearby_cells:
            target = random.choice(nearby_cells)
        else:
            target = enemy_cell

        # Randomize the phrasing
        templates = [
            f"move to {target} and shoot at anything in your sight",
            f"go to {target} and fire at enemies in sight",
            f"advance to {target} and shoot at targets in view",
            f"move to {target} and attack anything in sight",
        ]
        return random.choice(templates)

    def _generate_guard_near_enemy_strategy(self, enemy_cell: str) -> str:
        """Generate a guard strategy near the enemy's position."""
        # Get cells near the enemy for ambush positions
        nearby_cells = _get_cells_near_position(
            *self._last_enemy_pos if self._last_enemy_pos else (0, 0),
            radius_cells=2
        )

        if nearby_cells:
            guard_pos = random.choice(nearby_cells)
        else:
            guard_pos = enemy_cell

        templates = [
            f"guard {guard_pos} and shoot at anything in your sight",
            f"defend position {guard_pos} and fire at enemies in sight",
            f"hold {guard_pos} and attack targets in view",
        ]
        return random.choice(templates)

    def _generate_intercept_patrol_strategy(self, my_cell: str, enemy_cell: str) -> str:
        """Generate a patrol strategy to intercept the enemy."""
        # Create patrol route that crosses enemy's likely path
        # Get a cell between me and enemy
        nearby_enemy = _get_cells_near_position(
            *self._last_enemy_pos if self._last_enemy_pos else (0, 0),
            radius_cells=4
        )

        if len(nearby_enemy) >= 2:
            cell_a, cell_b = random.sample(nearby_enemy, 2)
        else:
            # Fallback: patrol around enemy cell
            cell_a = enemy_cell
            cell_b = nearby_enemy[0] if nearby_enemy else my_cell

        templates = [
            f"patrol between {cell_a} and {cell_b} and shoot at anything in your sight",
            f"go back and forth between {cell_a} and {cell_b} and fire at enemies in sight",
            f"circle between {cell_a} and {cell_b} and attack targets in view",
        ]
        return random.choice(templates)

    def _generate_approach_patrol_strategy(self, my_cell: str, enemy_cell: str) -> str:
        """Generate a patrol strategy that approaches the enemy."""
        # Get intermediate cells between me and enemy
        nearby_me = _get_cells_near_position(
            *self._last_enemy_pos if self._last_enemy_pos else (0, 0),
            radius_cells=6
        )

        # Pick cells that form a path toward the enemy
        if nearby_me:
            cell_a = random.choice(nearby_me)
            # Get another cell closer to enemy
            closer_cells = _get_cells_near_position(
                *self._last_enemy_pos if self._last_enemy_pos else (0, 0),
                radius_cells=3
            )
            cell_b = random.choice(closer_cells) if closer_cells else enemy_cell
        else:
            cell_a = my_cell
            cell_b = enemy_cell

        templates = [
            f"patrol between {cell_a} and {cell_b} and shoot at anything in your sight",
            f"alternate between {cell_a} and {cell_b} and fire at enemies in sight",
            f"loop between {cell_a} and {cell_b} and attack anything in view",
        ]
        return random.choice(templates)
