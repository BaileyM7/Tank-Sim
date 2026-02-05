"""Demo mode controller — cycles through scripted scenarios.

Runs on a daemon thread (same pattern as AIController). Each scenario
assigns a natural-language command string to both tanks, parses them
into high-level commands, and executes them tick-by-tick until the
scenario duration elapses or a tank dies.

The main game loop checks ``_request_reset`` each frame to know when
to respawn tanks for the next scenario.
"""
import time
from queue import Queue
from typing import List

from tanks.command_system import CommandExecutor, parse_command

# ---------------------------------------------------------------------------
# Pre-scripted demo scenarios
# ---------------------------------------------------------------------------

DEMO_SCENARIOS: List[dict] = [
    {
        "blue": "Move to I6",
        "red": "Move to J6",
        "duration": 6.0,
        "description": "Basic Movement",
    },
    {
        "blue": "Patrol between C3 and C9",
        "red": "Guard position P6",
        "duration": 12.0,
        "description": "Patrol & Guard",
    },
    {
        "blue": "Patrol between D2 and D10 and shoot at anything in your sight",
        "red": "Patrol between O2 and O10 and shoot at anything in your sight",
        "duration": 14.0,
        "description": "Combat Patrol",
    },
    {
        "blue": "Move to I3 and shoot at anything in your sight",
        "red": "Guard position J9 and shoot at anything in your sight",
        "duration": 12.0,
        "description": "Assault vs Defense",
    },
]


class DemoController:
    """Scenario sequencer for demo mode.

    Drives both tanks by writing TankCommand enums to their respective
    queues based on parsed high-level command strings.

    Attributes:
        scenario_display: The current scenario dict, read by the renderer
            to show overlay text.
        current_scenario_index: Index into DEMO_SCENARIOS.
    """

    TICK_INTERVAL = 1 / 30  # match game FPS

    def __init__(self, p1_queue: Queue, p2_queue: Queue, game_state,
                 level=None) -> None:
        self.p1_queue = p1_queue
        self.p2_queue = p2_queue
        self.game_state = game_state
        self.level = level              # Level for obstacle avoidance
        self._running = False
        self.current_scenario_index: int = 0
        self.scenario_display: dict = {}
        self._request_reset: bool = False

    def start(self) -> None:
        """Begin the demo loop. Call from a daemon thread."""
        self._running = True
        self._run_loop()

    def stop(self) -> None:
        """Signal the demo loop to stop."""
        self._running = False

    def _run_loop(self) -> None:
        while self._running:
            scenario = DEMO_SCENARIOS[self.current_scenario_index]
            self.scenario_display = scenario

            # Parse commands for both tanks
            blue_exec = CommandExecutor(level=self.level)
            blue_exec.set_commands(parse_command(scenario["blue"]))
            red_exec = CommandExecutor(level=self.level)
            red_exec.set_commands(parse_command(scenario["red"]))

            # Signal the main loop to respawn tanks
            self._request_reset = True

            # Wait until the main loop has reset and entered playing phase
            while self._running:
                snap = self.game_state.snapshot()
                if snap["phase"] == "playing" and not self._request_reset:
                    break
                time.sleep(0.05)

            # Execute scenario
            start_time = time.time()
            while self._running:
                snap = self.game_state.snapshot()
                if snap["phase"] != "playing":
                    break

                elapsed = time.time() - start_time
                if elapsed >= scenario["duration"]:
                    break

                me_blue = snap["tanks"].get("player1")
                me_red = snap["tanks"].get("player2")

                if me_blue and me_blue.get("alive"):
                    for cmd in blue_exec.tick(me_blue, me_red or {}):
                        self.p1_queue.put(cmd)

                if me_red and me_red.get("alive"):
                    for cmd in red_exec.tick(me_red, me_blue or {}):
                        self.p2_queue.put(cmd)

                time.sleep(self.TICK_INTERVAL)

            # Advance to next scenario (cycle)
            self.current_scenario_index = (
                (self.current_scenario_index + 1) % len(DEMO_SCENARIOS)
            )
