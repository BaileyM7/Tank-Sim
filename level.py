import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Tuple

from tanks.constants import (
    TerrainType, ObstacleType, Facing,
    OBSTACLE_DEFS, OBSTACLE_BLOCKS,
)


@dataclass
class ObstaclePlacement:
    type: ObstacleType
    col: int
    row: int
    span_w: int = 1
    span_h: int = 1


@dataclass
class SpawnPoint:
    col: int
    row: int
    facing: Facing


@dataclass
class Level:
    name: str
    version: int
    columns: int
    rows: int
    cell_size: int
    terrain: List[List[TerrainType]]
    obstacles: List[ObstaclePlacement]
    spawns: dict  # {"player1": SpawnPoint, "player2": SpawnPoint}
    collision_map: List[List[bool]] = field(default_factory=list)

    def __post_init__(self):
        if not self.collision_map:
            self.collision_map = self.build_collision_map()

    def build_collision_map(self) -> List[List[bool]]:
        grid = [[False] * self.columns for _ in range(self.rows)]
        for obs in self.obstacles:
            if not OBSTACLE_BLOCKS.get(obs.type, True):
                continue
            for dr in range(obs.span_h):
                for dc in range(obs.span_w):
                    r = obs.row + dr
                    c = obs.col + dc
                    if 0 <= r < self.rows and 0 <= c < self.columns:
                        grid[r][c] = True
        return grid

    def is_passable(self, col: int, row: int) -> bool:
        if not (0 <= col < self.columns and 0 <= row < self.rows):
            return False
        return not self.collision_map[row][col]

    def get_blocked_cells(self) -> List[Tuple[int, int]]:
        blocked = []
        for r in range(self.rows):
            for c in range(self.columns):
                if self.collision_map[r][c]:
                    blocked.append((c, r))
        return blocked


def load_level(filepath: Path) -> Level:
    with open(filepath, "r") as f:
        data = json.load(f)

    terrain = []
    for row_data in data["terrain"]:
        terrain.append([TerrainType(cell) for cell in row_data])

    obstacles = []
    for obs_data in data["obstacles"]:
        obs_type = ObstacleType(obs_data["type"])
        _, _, def_w, def_h = OBSTACLE_DEFS[obs_type]
        span = obs_data.get("span", [def_w, def_h])
        obstacles.append(ObstaclePlacement(
            type=obs_type,
            col=obs_data["col"],
            row=obs_data["row"],
            span_w=span[0],
            span_h=span[1],
        ))

    spawns = {}
    for key in ["player1", "player2"]:
        sp = data["spawns"][key]
        spawns[key] = SpawnPoint(
            col=sp["col"],
            row=sp["row"],
            facing=Facing(sp["facing"]),
        )

    return Level(
        name=data.get("name", "Untitled"),
        version=data.get("version", 1),
        columns=data["grid"]["columns"],
        rows=data["grid"]["rows"],
        cell_size=data["grid"]["cell_size"],
        terrain=terrain,
        obstacles=obstacles,
        spawns=spawns,
    )


def save_level(level: Level, filepath: Path) -> None:
    data = {
        "name": level.name,
        "version": level.version,
        "grid": {
            "columns": level.columns,
            "rows": level.rows,
            "cell_size": level.cell_size,
        },
        "terrain": [
            [cell.value for cell in row]
            for row in level.terrain
        ],
        "obstacles": [
            {
                "type": obs.type.value,
                "col": obs.col,
                "row": obs.row,
                **({"span": [obs.span_w, obs.span_h]}
                   if (obs.span_w, obs.span_h) != (1, 1) else {}),
            }
            for obs in level.obstacles
        ],
        "spawns": {
            key: {
                "col": sp.col,
                "row": sp.row,
                "facing": sp.facing.value,
            }
            for key, sp in level.spawns.items()
        },
    }
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
