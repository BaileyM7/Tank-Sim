"""Shared game state between Pygame loop, API server, and AI."""
import threading
from dataclasses import dataclass, field
from typing import List, Dict, Optional

from tanks.constants import GamePhase, GameMode, TANK_MAX_HEALTH


@dataclass
class TankState:
    """Snapshot of a single tank's state, safe to serialize to JSON."""
    color: str
    x: float
    y: float
    angle: float
    health: int
    alive: bool
    bullets: List[Dict]


@dataclass
class GameState:
    """Full game snapshot. Written by game loop, read by API and AI."""
    phase: GamePhase = GamePhase.TITLE_SCREEN
    mode: Optional[GameMode] = None
    tick: int = 0
    tanks: Dict[str, TankState] = field(default_factory=dict)
    winner: Optional[str] = None
    strategies: Dict[str, Optional[str]] = field(
        default_factory=lambda: {"player1": None, "player2": None}
    )
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def snapshot(self) -> dict:
        """Return a JSON-serializable dictionary of the full game state."""
        with self._lock:
            return {
                "phase": self.phase.value,
                "mode": self.mode.value if self.mode else None,
                "tick": self.tick,
                "tanks": {
                    name: {
                        "color": ts.color,
                        "x": round(ts.x, 1),
                        "y": round(ts.y, 1),
                        "angle": round(ts.angle, 1),
                        "health": ts.health,
                        "alive": ts.alive,
                        "bullets": ts.bullets,
                    }
                    for name, ts in self.tanks.items()
                },
                "winner": self.winner,
                "strategies": dict(self.strategies),
            }

    def set_strategy(self, player: str, text: Optional[str]) -> None:
        """Set the active natural language strategy for a player."""
        with self._lock:
            self.strategies[player] = text

    def update_tank(self, name: str, tank) -> None:
        """Update a tank's entry from a Tank object. Called by game loop."""
        with self._lock:
            self.tanks[name] = TankState(
                color=tank.color,
                x=tank.x,
                y=tank.y,
                angle=tank.angle,
                health=tank.health,
                alive=tank.alive,
                bullets=[
                    {"x": round(b.x, 1), "y": round(b.y, 1), "angle": round(b.angle, 1)}
                    for b in tank.bullets
                ],
            )
