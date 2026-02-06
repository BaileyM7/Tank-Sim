import math
import pygame
from typing import List

from tanks.constants import (
    CELL_SIZE, WINDOW_WIDTH, WINDOW_HEIGHT,
    TANK_SPEED, TANK_ROTATION_SPEED, TANK_HITBOX_HALF,
    BULLET_SPEED, BULLET_COOLDOWN_MS,
    SHOOT_SLOWDOWN_MS, SHOOT_SPEED_FACTOR,
    TANK_MAX_HEALTH, BULLET_DAMAGE, TankCommand,
)
from tanks.level import Level


class Bullet:
    def __init__(self, x: float, y: float, angle: float, color: str) -> None:
        self.x = x
        self.y = y
        self.angle = angle
        self.color = color
        self.alive = True
        rad = math.radians(angle)
        self.dx = math.sin(rad) * BULLET_SPEED
        self.dy = -math.cos(rad) * BULLET_SPEED

    def update(self, level: Level) -> None:
        self.x += self.dx
        self.y += self.dy

        # Off-screen check
        if not (0 <= self.x <= WINDOW_WIDTH and 0 <= self.y <= WINDOW_HEIGHT):
            self.alive = False
            return

        # Grid collision
        col = int(self.x // CELL_SIZE)
        row = int(self.y // CELL_SIZE)
        if not level.is_passable(col, row):
            self.alive = False


class Tank:
    def __init__(self, x: float, y: float, angle: float, color: str, speed_multiplier: float = 1.0) -> None:
        self.x = x
        self.y = y
        self.angle = angle  # 0=up, 90=right, 180=down, 270=left
        self.color = color
        self.bullets: List[Bullet] = []
        self._last_shot_time = 0
        self.health: int = TANK_MAX_HEALTH
        self.alive: bool = True
        self.speed_multiplier: float = speed_multiplier

    def _current_speed(self) -> float:
        """Return movement speed, reduced briefly after firing."""
        now = pygame.time.get_ticks()
        base_speed = TANK_SPEED * self.speed_multiplier
        if now - self._last_shot_time < SHOOT_SLOWDOWN_MS:
            return base_speed * SHOOT_SPEED_FACTOR
        return base_speed

    def handle_input(self, keys, level: Level) -> None:
        if not self.alive:
            return

        # Rotation: A/D
        if keys[pygame.K_a]:
            self.angle = (self.angle - TANK_ROTATION_SPEED) % 360
        if keys[pygame.K_d]:
            self.angle = (self.angle + TANK_ROTATION_SPEED) % 360

        # Movement: W/S
        speed = self._current_speed()
        rad = math.radians(self.angle)
        dx = math.sin(rad) * speed
        dy = -math.cos(rad) * speed

        if keys[pygame.K_w]:
            nx, ny = self.x + dx, self.y + dy
            if self._can_move_to(nx, ny, level):
                self.x, self.y = nx, ny
        if keys[pygame.K_s]:
            nx, ny = self.x - dx, self.y - dy
            if self._can_move_to(nx, ny, level):
                self.x, self.y = nx, ny

        # Shoot: Space
        if keys[pygame.K_SPACE]:
            self._try_shoot()

    def _try_shoot(self) -> None:
        now = pygame.time.get_ticks()
        cooldown_elapsed = now - self._last_shot_time
        if cooldown_elapsed >= BULLET_COOLDOWN_MS:
            self._last_shot_time = now
            rad = math.radians(self.angle)
            spawn_dist = CELL_SIZE * 0.45
            bx = self.x + math.sin(rad) * spawn_dist
            by = self.y - math.cos(rad) * spawn_dist
            self.bullets.append(Bullet(bx, by, self.angle, self.color))
            print(f"Tank {self.color} fired bullet! Total bullets: {len(self.bullets)}")
        else:
            print(f"Tank {self.color} shoot blocked by cooldown: {cooldown_elapsed}ms < {BULLET_COOLDOWN_MS}ms")

    def apply_command(self, command: TankCommand, level: Level) -> None:
        if not self.alive:
            print(f"Tank {self.color} apply_command: not alive, ignoring {command}")
            return

        # First, check if we're stuck and need to force unstuck
        if not self._can_move_to(self.x, self.y, level):
            print(f"Tank {self.color} is stuck at ({self.x:.1f}, {self.y:.1f}), force unstucking")
            self._force_unstuck(level)
            return

        print(f"Tank {self.color} applying command: {command}")

        if command == TankCommand.ROTATE_LEFT:
            self.angle = (self.angle - TANK_ROTATION_SPEED) % 360
        elif command == TankCommand.ROTATE_RIGHT:
            self.angle = (self.angle + TANK_ROTATION_SPEED) % 360
        elif command == TankCommand.FORWARD:
            speed = self._current_speed()
            rad = math.radians(self.angle)
            nx = self.x + math.sin(rad) * speed
            ny = self.y - math.cos(rad) * speed
            if self._can_move_to(nx, ny, level):
                self.x, self.y = nx, ny
        elif command == TankCommand.BACKWARD:
            speed = self._current_speed()
            rad = math.radians(self.angle)
            nx = self.x - math.sin(rad) * speed
            ny = self.y + math.cos(rad) * speed
            if self._can_move_to(nx, ny, level):
                self.x, self.y = nx, ny
        elif command == TankCommand.SHOOT:
            self._try_shoot()

    def take_damage(self, amount: int = BULLET_DAMAGE) -> None:
        self.health -= amount
        if self.health <= 0:
            self.health = 0
            self.alive = False

    def update_bullets(self, level: Level) -> None:
        for b in self.bullets:
            b.update(level)
        self.bullets = [b for b in self.bullets if b.alive]

    def _can_move_to(self, nx: float, ny: float, level: Level) -> bool:
        h = TANK_HITBOX_HALF
        corners = [
            (nx - h, ny - h),
            (nx + h, ny - h),
            (nx - h, ny + h),
            (nx + h, ny + h),
        ]
        for cx, cy in corners:
            col = int(cx // CELL_SIZE)
            row = int(cy // CELL_SIZE)
            if not level.is_passable(col, row):
                return False
        return True

    def _force_unstuck(self, level: Level) -> None:
        """Push the tank out of walls when stuck."""
        h = TANK_HITBOX_HALF
        corners = [
            (self.x - h, self.y - h),
            (self.x + h, self.y - h),
            (self.x - h, self.y + h),
            (self.x + h, self.y + h),
        ]

        # Find which corners are in walls
        push_x, push_y = 0.0, 0.0
        stuck_count = 0

        for cx, cy in corners:
            col = int(cx // CELL_SIZE)
            row = int(cy // CELL_SIZE)
            if not level.is_passable(col, row):
                # Calculate push direction away from this blocked cell
                cell_center_x = col * CELL_SIZE + CELL_SIZE / 2
                cell_center_y = row * CELL_SIZE + CELL_SIZE / 2
                push_x += self.x - cell_center_x
                push_y += self.y - cell_center_y
                stuck_count += 1

        if stuck_count > 0:
            # Normalize and push out
            magnitude = math.sqrt(push_x * push_x + push_y * push_y)
            if magnitude > 0:
                push_x = (push_x / magnitude) * TANK_SPEED * 2
                push_y = (push_y / magnitude) * TANK_SPEED * 2

                # Try to move in the push direction
                nx = self.x + push_x
                ny = self.y + push_y

                # Force the movement (don't check collision for unstuck)
                self.x = nx
                self.y = ny


def check_bullet_tank_collisions(tanks: List[Tank]) -> None:
    """Check all bullets against all tanks, applying damage on hit."""
    for shooter in tanks:
        for bullet in shooter.bullets:
            if not bullet.alive:
                continue
            for target in tanks:
                if target.color == bullet.color:
                    continue
                if not target.alive:
                    continue
                dx = bullet.x - target.x
                dy = bullet.y - target.y
                if dx * dx + dy * dy <= TANK_HITBOX_HALF ** 2:
                    bullet.alive = False
                    target.take_damage()
