"""Game history tracking for commands and periodic snapshots.

Provides thread-safe logging of all commands sent to tanks and periodic
snapshots of game state. Designed to be queried via API endpoints.
"""
import time
import threading
from collections import deque
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional


@dataclass
class CommandLogEntry:
    """A single command log entry."""
    timestamp: float
    tick: int
    player: str
    command: str
    command_type: str  # "direct" or "strategy"


@dataclass
class SnapshotLogEntry:
    """A periodic snapshot of game state."""
    timestamp: float
    tick: int
    tanks: Dict
    phase: str
    mode: Optional[str]


class GameHistory:
    """Thread-safe game history tracker with bounded memory.

    Tracks:
    - All commands sent to tanks
    - Periodic snapshots of game state (every 5 seconds / 150 frames at 30 FPS)

    Uses circular buffers (deques) to automatically evict old entries when full.
    """

    def __init__(self, max_commands: int = 1000, max_snapshots: int = 100):
        """Initialize game history tracker.

        Args:
            max_commands: Maximum number of command entries to keep
            max_snapshots: Maximum number of snapshot entries to keep
        """
        self._commands = deque(maxlen=max_commands)
        self._snapshots = deque(maxlen=max_snapshots)
        self._lock = threading.Lock()
        self._last_snapshot_tick = 0
        self._snapshot_interval = 150  # 5 seconds at 30 FPS

    def log_command(self, tick: int, player: str, command: str, command_type: str) -> None:
        """Log a command sent to a tank.

        Args:
            tick: Current game tick number
            player: Player identifier ("player1" or "player2")
            command: Command value or strategy text
            command_type: "direct" or "strategy"
        """
        entry = CommandLogEntry(
            timestamp=time.time(),
            tick=tick,
            player=player,
            command=command,
            command_type=command_type,
        )
        with self._lock:
            self._commands.append(entry)

    def log_snapshot(self, tick: int, game_state_snapshot: dict) -> None:
        """Log a periodic snapshot of game state.

        Args:
            tick: Current game tick number
            game_state_snapshot: Full game state from GameState.snapshot()
        """
        entry = SnapshotLogEntry(
            timestamp=time.time(),
            tick=tick,
            tanks=game_state_snapshot.get("tanks", {}),
            phase=game_state_snapshot.get("phase", "UNKNOWN"),
            mode=game_state_snapshot.get("mode"),
        )
        with self._lock:
            self._snapshots.append(entry)
            self._last_snapshot_tick = tick

    def should_snapshot(self, current_tick: int) -> bool:
        """Check if it's time to take a snapshot.

        Args:
            current_tick: Current game tick number

        Returns:
            True if a snapshot should be taken
        """
        return current_tick - self._last_snapshot_tick >= self._snapshot_interval

    def get_history(
        self,
        since_tick: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """Get game history with optional filtering.

        Args:
            since_tick: Only return entries after this tick (inclusive)
            limit: Maximum number of entries to return per category

        Returns:
            Dictionary with commands, snapshots, and metadata
        """
        with self._lock:
            # Filter and convert commands
            commands = list(self._commands)
            if since_tick is not None:
                commands = [c for c in commands if c.tick >= since_tick]
            if limit is not None:
                commands = commands[-limit:]

            # Filter and convert snapshots
            snapshots = list(self._snapshots)
            if since_tick is not None:
                snapshots = [s for s in snapshots if s.tick >= since_tick]
            if limit is not None:
                snapshots = snapshots[-limit:]

            # Calculate metadata
            all_ticks = (
                [c.tick for c in self._commands]
                + [s.tick for s in self._snapshots]
            )
            oldest_tick = min(all_ticks) if all_ticks else 0
            newest_tick = max(all_ticks) if all_ticks else 0

            return {
                "commands": [asdict(c) for c in commands],
                "snapshots": [asdict(s) for s in snapshots],
                "total_commands": len(commands),
                "total_snapshots": len(snapshots),
                "oldest_tick": oldest_tick,
                "newest_tick": newest_tick,
            }
