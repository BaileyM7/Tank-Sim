import random
import pygame
from typing import Dict, Tuple

from tanks.constants import (
    CELL_SIZE, TerrainType, ObstacleType,
    TERRAIN_FILES, OBSTACLE_DEFS, PLAYER_TANK_COLORS,
    ENVIRONMENT_DIR, OBSTACLES_DIR, TANKS_DIR, BULLETS_DIR,
)


class AssetManager:
    def __init__(self) -> None:
        self._terrain_cache: Dict[TerrainType, pygame.Surface] = {}
        self._obstacle_cache: Dict[Tuple[ObstacleType, int, int], pygame.Surface] = {}
        self._tank_cache: Dict[str, pygame.Surface] = {}

    def load_all(self) -> None:
        self._load_terrain()
        self._load_obstacles()
        self._load_tanks()
        self._load_bullets()
        self._generate_dirt_transitions()

    def _load_terrain(self) -> None:
        for terrain_type, filename in TERRAIN_FILES.items():
            path = ENVIRONMENT_DIR / filename
            surface = pygame.image.load(str(path)).convert()
            scaled = pygame.transform.smoothscale(surface, (CELL_SIZE, CELL_SIZE))
            self._terrain_cache[terrain_type] = scaled

    def _load_obstacles(self) -> None:
        for obs_type, (directory, filename, def_w, def_h) in OBSTACLE_DEFS.items():
            path = directory / filename
            surface = pygame.image.load(str(path)).convert_alpha()
            target_w = def_w * CELL_SIZE
            target_h = def_h * CELL_SIZE
            scaled = pygame.transform.smoothscale(surface, (target_w, target_h))
            self._obstacle_cache[(obs_type, def_w, def_h)] = scaled

    def _load_tanks(self) -> None:
        for player_num, color in PLAYER_TANK_COLORS.items():
            # Tank body
            body_path = TANKS_DIR / f"tank{color}.png"
            body_surf = pygame.image.load(str(body_path)).convert_alpha()
            body_scaled = _scale_to_fit(body_surf, CELL_SIZE, CELL_SIZE)
            self._tank_cache[f"{color}_body"] = body_scaled

            # Gun barrel
            barrel_path = TANKS_DIR / f"barrel{color}.png"
            barrel_surf = pygame.image.load(str(barrel_path)).convert_alpha()
            barrel_h = int(CELL_SIZE * 0.6)
            ratio = barrel_h / barrel_surf.get_height()
            barrel_w = max(1, int(barrel_surf.get_width() * ratio))
            barrel_scaled = pygame.transform.smoothscale(barrel_surf, (barrel_w, barrel_h))
            self._tank_cache[f"{color}_barrel"] = barrel_scaled

    def get_terrain(self, terrain_type: TerrainType) -> pygame.Surface:
        return self._terrain_cache[terrain_type]

    def get_obstacle(self, obs_type: ObstacleType,
                     span_w: int = None, span_h: int = None) -> pygame.Surface:
        if span_w is None or span_h is None:
            _, _, dw, dh = OBSTACLE_DEFS[obs_type]
            span_w = span_w or dw
            span_h = span_h or dh
        key = (obs_type, span_w, span_h)
        if key not in self._obstacle_cache:
            directory, filename = OBSTACLE_DEFS[obs_type][0], OBSTACLE_DEFS[obs_type][1]
            path = directory / filename
            surface = pygame.image.load(str(path)).convert_alpha()
            scaled = pygame.transform.smoothscale(
                surface, (span_w * CELL_SIZE, span_h * CELL_SIZE)
            )
            self._obstacle_cache[key] = scaled
        return self._obstacle_cache[key]

    def _load_bullets(self) -> None:
        for player_num, color in PLAYER_TANK_COLORS.items():
            path = BULLETS_DIR / f"bullet{color}.png"
            surf = pygame.image.load(str(path)).convert_alpha()
            scaled = pygame.transform.smoothscale(surf, (16, 32))
            self._tank_cache[f"{color}_bullet"] = scaled

    def _generate_dirt_transitions(self) -> None:
        """Generate 4 directional dirt-on-sand transition overlays."""
        dirt_tile = self._terrain_cache[TerrainType.DIRT]
        dirt_color = dirt_tile.get_at((CELL_SIZE // 2, CELL_SIZE // 2))[:3]

        rng = random.Random(42)

        for direction in ("left", "right", "top", "bottom"):
            surf = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
            for _ in range(150):
                t = rng.random()
                if rng.random() > (1.0 - t) ** 1.4:
                    continue
                x, y = self._transition_pos(direction, t, rng)
                radius = rng.randint(10, 18)
                alpha = int(230 * (1.0 - t) ** 0.8)
                r = max(0, min(255, dirt_color[0] + rng.randint(-15, 15)))
                g = max(0, min(255, dirt_color[1] + rng.randint(-15, 15)))
                b = max(0, min(255, dirt_color[2] + rng.randint(-15, 15)))
                pygame.draw.circle(surf, (r, g, b, alpha), (x, y), radius)
            self._terrain_cache[f"transition_{direction}"] = surf

    @staticmethod
    def _transition_pos(direction: str, t: float, rng) -> tuple:
        if direction == "right":
            return int((1.0 - t) * CELL_SIZE), rng.randint(0, CELL_SIZE - 1)
        elif direction == "left":
            return int(t * CELL_SIZE), rng.randint(0, CELL_SIZE - 1)
        elif direction == "bottom":
            return rng.randint(0, CELL_SIZE - 1), int((1.0 - t) * CELL_SIZE)
        else:  # top
            return rng.randint(0, CELL_SIZE - 1), int(t * CELL_SIZE)

    def get_dirt_transition(self, direction: str) -> pygame.Surface:
        """Get a directional dirt transition overlay ('left','right','top','bottom')."""
        return self._terrain_cache[f"transition_{direction}"]

    def get_bullet(self, color: str) -> pygame.Surface:
        return self._tank_cache[f"{color}_bullet"]

    def get_tank_body(self, color: str) -> pygame.Surface:
        return self._tank_cache[f"{color}_body"]

    def get_tank_barrel(self, color: str) -> pygame.Surface:
        return self._tank_cache[f"{color}_barrel"]


def _scale_to_fit(surface: pygame.Surface, max_w: int, max_h: int) -> pygame.Surface:
    orig_w, orig_h = surface.get_size()
    ratio = min(max_w / orig_w, max_h / orig_h)
    new_w = max(1, int(orig_w * ratio))
    new_h = max(1, int(orig_h * ratio))
    return pygame.transform.smoothscale(surface, (new_w, new_h))
