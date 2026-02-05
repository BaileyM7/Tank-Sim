import math
import pygame
from typing import List

from tanks.constants import (
    CELL_SIZE, WINDOW_WIDTH, WINDOW_HEIGHT,
    PLAYER_TANK_COLORS, FACING_ANGLES, TerrainType,
    TANK_HITBOX_HALF, TANK_MAX_HEALTH,
)
from tanks.assets import AssetManager
from tanks.level import Level


class LevelRenderer:
    def __init__(self, screen: pygame.Surface, assets: AssetManager) -> None:
        self.screen = screen
        self.assets = assets
        self.show_grid = False
        self.show_collision = False
        self._label_font = None

    def render(self, level: Level, tanks: List = None) -> None:
        self._draw_terrain(level)
        self._draw_terrain_transitions(level)
        self._draw_obstacles(level)
        if tanks:
            for t in tanks:
                self._draw_bullets(t)
                self._draw_tank(t)
            self._draw_hud(tanks)
        else:
            self._draw_spawns(level)
        if self.show_grid:
            self._draw_grid_overlay(level)
        if self.show_collision:
            self._draw_collision_overlay(level)

    def _draw_terrain(self, level: Level) -> None:
        for row in range(level.rows):
            for col in range(level.columns):
                terrain_type = level.terrain[row][col]
                tile = self.assets.get_terrain(terrain_type)
                self.screen.blit(tile, (col * CELL_SIZE, row * CELL_SIZE))

    def _draw_terrain_transitions(self, level: Level) -> None:
        """Overlay dirt splotches biased toward the sand side of the border.

        The overlay is shifted so ~1/3 sits on the dirt side and ~2/3 on sand.
        """
        third = CELL_SIZE // 3
        for row in range(level.rows):
            for col in range(level.columns):
                if level.terrain[row][col] != TerrainType.SAND:
                    continue
                px = col * CELL_SIZE
                py = row * CELL_SIZE
                if col > 0 and level.terrain[row][col - 1] == TerrainType.DIRT:
                    self.screen.blit(self.assets.get_dirt_transition("left"), (px - third, py))
                if col < level.columns - 1 and level.terrain[row][col + 1] == TerrainType.DIRT:
                    self.screen.blit(self.assets.get_dirt_transition("right"), (px + third, py))
                if row > 0 and level.terrain[row - 1][col] == TerrainType.DIRT:
                    self.screen.blit(self.assets.get_dirt_transition("top"), (px, py - third))
                if row < level.rows - 1 and level.terrain[row + 1][col] == TerrainType.DIRT:
                    self.screen.blit(self.assets.get_dirt_transition("bottom"), (px, py + third))

    def _draw_obstacles(self, level: Level) -> None:
        for obs in level.obstacles:
            surface = self.assets.get_obstacle(obs.type, obs.span_w, obs.span_h)
            pixel_x = obs.col * CELL_SIZE
            pixel_y = obs.row * CELL_SIZE
            # Center sprite within its span area
            span_pixel_w = obs.span_w * CELL_SIZE
            span_pixel_h = obs.span_h * CELL_SIZE
            offset_x = (span_pixel_w - surface.get_width()) // 2
            offset_y = (span_pixel_h - surface.get_height()) // 2
            self.screen.blit(surface, (pixel_x + offset_x, pixel_y + offset_y))

    def _draw_spawns(self, level: Level) -> None:
        for key, spawn in level.spawns.items():
            player_num = int(key[-1])
            color = PLAYER_TANK_COLORS[player_num]

            body = self.assets.get_tank_body(color)
            barrel = self.assets.get_tank_barrel(color)

            angle = FACING_ANGLES[spawn.facing]
            body_rot = pygame.transform.rotate(body, angle)
            barrel_rot = pygame.transform.rotate(barrel, angle)

            cx = spawn.col * CELL_SIZE + CELL_SIZE // 2
            cy = spawn.row * CELL_SIZE + CELL_SIZE // 2

            body_rect = body_rot.get_rect(center=(cx, cy))
            self.screen.blit(body_rot, body_rect)

            # Offset barrel in the facing direction
            barrel_rect = barrel_rot.get_rect(center=(cx, cy))
            self.screen.blit(barrel_rot, barrel_rect)

    def _draw_tank(self, tank) -> None:
        if not tank.alive:
            return
        body = self.assets.get_tank_body(tank.color)
        barrel = self.assets.get_tank_barrel(tank.color)

        # pygame.transform.rotate uses CCW degrees; our angle is CW from north
        pg_angle = -tank.angle
        body_rot = pygame.transform.rotate(body, pg_angle)
        barrel_rot = pygame.transform.rotate(barrel, pg_angle)

        cx, cy = tank.x, tank.y
        body_rect = body_rot.get_rect(center=(cx, cy))
        self.screen.blit(body_rot, body_rect)

        # Offset barrel forward from center
        rad = math.radians(tank.angle)
        offset = CELL_SIZE * 0.12
        bx = cx + math.sin(rad) * offset
        by = cy - math.cos(rad) * offset
        barrel_rect = barrel_rot.get_rect(center=(bx, by))
        self.screen.blit(barrel_rot, barrel_rect)

    def _draw_bullets(self, tank) -> None:
        for b in tank.bullets:
            sprite = self.assets.get_bullet(b.color)
            pg_angle = -b.angle
            rotated = pygame.transform.rotate(sprite, pg_angle)
            rect = rotated.get_rect(center=(b.x, b.y))
            self.screen.blit(rotated, rect)

    def _draw_grid_overlay(self, level: Level) -> None:
        grid_surface = pygame.Surface(
            (WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA
        )
        color = (0, 0, 0, 120)
        dash_len = 8
        gap_len = 8

        # Vertical dashed lines
        for col in range(level.columns + 1):
            x = col * CELL_SIZE
            y = 0
            while y < WINDOW_HEIGHT:
                end_y = min(y + dash_len, WINDOW_HEIGHT)
                pygame.draw.line(grid_surface, color, (x, y), (x, end_y))
                y += dash_len + gap_len

        # Horizontal dashed lines
        for row in range(level.rows + 1):
            y = row * CELL_SIZE
            x = 0
            while x < WINDOW_WIDTH:
                end_x = min(x + dash_len, WINDOW_WIDTH)
                pygame.draw.line(grid_surface, color, (x, y), (end_x, y))
                x += dash_len + gap_len

        self.screen.blit(grid_surface, (0, 0))

        # Chess-style labels: letters (A-P) across columns, numbers (1-12) down rows
        if self._label_font is None:
            self._label_font = pygame.font.SysFont("consolas", 24, bold=True)

        label_bg = (0, 0, 0, 160)
        for col in range(level.columns):
            letter = chr(ord('A') + col)
            text = self._label_font.render(letter, True, (255, 255, 255))
            # Background pill behind label
            bg = pygame.Surface(
                (text.get_width() + 8, text.get_height() + 4), pygame.SRCALPHA
            )
            bg.fill(label_bg)
            tx = col * CELL_SIZE + (CELL_SIZE - bg.get_width()) // 2
            self.screen.blit(bg, (tx, 2))
            self.screen.blit(text, (tx + 4, 4))

        for row in range(level.rows):
            number = str(row + 1)
            text = self._label_font.render(number, True, (255, 255, 255))
            bg = pygame.Surface(
                (text.get_width() + 8, text.get_height() + 4), pygame.SRCALPHA
            )
            bg.fill(label_bg)
            ty = row * CELL_SIZE + (CELL_SIZE - bg.get_height()) // 2
            self.screen.blit(bg, (2, ty))
            self.screen.blit(text, (6, ty + 2))

    def _draw_collision_overlay(self, level: Level) -> None:
        overlay = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
        overlay.fill((255, 0, 0, 60))
        for col, row in level.get_blocked_cells():
            self.screen.blit(overlay, (col * CELL_SIZE, row * CELL_SIZE))

    # ---- HUD ----

    def _draw_hud(self, tanks) -> None:
        """Draw health bars above each alive tank."""
        for tank in tanks:
            if not tank.alive:
                continue
            bar_w = 80
            bar_h = 10
            bar_x = tank.x - bar_w // 2
            bar_y = tank.y - TANK_HITBOX_HALF - 24
            pygame.draw.rect(self.screen, (60, 60, 60), (bar_x, bar_y, bar_w, bar_h))
            fill_w = int(bar_w * (tank.health / TANK_MAX_HEALTH))
            fill_color = (0, 200, 0) if tank.health > 1 else (200, 0, 0)
            pygame.draw.rect(self.screen, fill_color, (bar_x, bar_y, fill_w, bar_h))

    # ---- Title Screen ----

    def render_title_screen(self, selected_index: int) -> None:
        """Render title screen with 1P / 2P mode selection."""
        self.screen.fill((40, 35, 30))

        # Title
        title_font = pygame.font.SysFont("consolas", 104, bold=True)
        title_surf = title_font.render("TANK ARENA", True, (220, 200, 160))
        title_rect = title_surf.get_rect(center=(WINDOW_WIDTH // 2, 300))
        self.screen.blit(title_surf, title_rect)

        # Decorative tanks
        blue_body = self.assets.get_tank_body("Blue")
        red_body = self.assets.get_tank_body("Red")
        blue_rot = pygame.transform.rotate(blue_body, -90)
        self.screen.blit(blue_rot, blue_rot.get_rect(center=(400, 300)))
        red_rot = pygame.transform.rotate(red_body, 90)
        self.screen.blit(red_rot, red_rot.get_rect(center=(1400, 300)))

        # Menu options
        option_font = pygame.font.SysFont("consolas", 64)
        options = ["1 Player", "2 Players", "Manual", "Demo"]
        for i, label in enumerate(options):
            color = (255, 255, 100) if i == selected_index else (180, 170, 140)
            prefix = "> " if i == selected_index else "  "
            surf = option_font.render(prefix + label, True, color)
            rect = surf.get_rect(center=(WINDOW_WIDTH // 2, 600 + i * 100))
            self.screen.blit(surf, rect)

        # Instructions
        hint_font = pygame.font.SysFont("consolas", 32)
        hint = hint_font.render(
            "UP/DOWN to select, ENTER to start, ESC to quit",
            True, (120, 110, 100),
        )
        self.screen.blit(hint, hint.get_rect(center=(WINDOW_WIDTH // 2, 1000)))

    # ---- Game Over ----

    def render_game_over(self, winner_color: str) -> None:
        """Overlay game-over banner on top of the current frame."""
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        font = pygame.font.SysFont("consolas", 96, bold=True)
        text = font.render(f"{winner_color} Tank Wins!", True, (255, 255, 100))
        self.screen.blit(
            text, text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 60))
        )

        sub_font = pygame.font.SysFont("consolas", 44)
        hint = sub_font.render(
            "Press ESC to return to title",
            True, (200, 190, 170),
        )
        self.screen.blit(
            hint, hint.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 80))
        )

    # ---- Demo Overlay ----

    def render_demo_overlay(self, scenario: dict,
                            scenario_index: int, total: int) -> None:
        """Draw a banner at the top showing current demo commands."""
        if not scenario:
            return

        banner_h = 210
        banner = pygame.Surface((WINDOW_WIDTH, banner_h), pygame.SRCALPHA)
        banner.fill((0, 0, 0, 180))
        self.screen.blit(banner, (0, 0))

        title_font = pygame.font.SysFont("consolas", 36, bold=True)
        cmd_font = pygame.font.SysFont("consolas", 28)
        hint_font = pygame.font.SysFont("consolas", 24)

        # Line 1: "DEMO MODE - <description>  (Example n/total)"
        desc = scenario.get("description", "")
        header = f"DEMO MODE - {desc}  (Example {scenario_index + 1}/{total})"
        header_surf = title_font.render(header, True, (255, 255, 255))
        self.screen.blit(
            header_surf,
            header_surf.get_rect(center=(WINDOW_WIDTH // 2, 32)),
        )

        # Line 2: Blue command
        blue_text = f"Blue: {scenario.get('blue', '')}"
        blue_surf = cmd_font.render(blue_text, True, (120, 160, 255))
        self.screen.blit(blue_surf, (32, 76))

        # Line 3: Red command (on its own line below blue)
        red_text = f"Red: {scenario.get('red', '')}"
        red_surf = cmd_font.render(red_text, True, (255, 130, 120))
        self.screen.blit(red_surf, (32, 112))

        # Hint at bottom of banner
        hint_surf = hint_font.render(
            "Press ESC to return to title", True, (140, 130, 120),
        )
        self.screen.blit(
            hint_surf,
            hint_surf.get_rect(center=(WINDOW_WIDTH // 2, 172)),
        )
