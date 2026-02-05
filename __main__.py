"""Entry point: python -m tanks [--manual] [level_file]

Modes:
    (default)  Title screen -> 1P or 2P game via API
    --manual   Drive a tank with WASD, shoot with Space (legacy mode)

Keyboard controls (manual mode):
    W/S   - forward / backward
    A/D   - rotate left / right
    Space - shoot
    G     - toggle grid overlay
    C     - toggle collision map overlay
    ESC   - quit

Title screen controls:
    UP/DOWN - select mode
    ENTER   - start game
    ESC     - quit
"""

import sys
import threading
from queue import Queue, Empty
from pathlib import Path

import pygame

from tanks.constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE, FPS, LEVELS_DIR,
    CELL_SIZE, PLAYER_TANK_COLORS, FACING_TO_ANGLE,
    GamePhase, GameMode, API_HOST, API_PORT, TankCommand,
)
from tanks.assets import AssetManager
from tanks.level import load_level
from tanks.renderer import LevelRenderer
from tanks.tank import Tank, check_bullet_tank_collisions
from tanks.game_state import GameState
from tanks.game_history import GameHistory
from tanks.tank_api import run_tank_api
from tanks.ai_controller import AIController
from tanks.demo_controller import DemoController, DEMO_SCENARIOS
from tanks.navigation import is_in_sight, angle_to_target, angle_error
from tanks.obstacle_avoidance import ObstacleAvoider
from tanks.command_system import CommandExecutor


def _apply_with_avoidance(tank, cmd, level, avoider):
    """Apply a command with obstacle avoidance for API-controlled tanks.

    When a FORWARD command would drive the tank into an obstacle, the
    avoidance system replaces it with steering commands to navigate
    around the obstruction automatically.
    """
    if cmd == TankCommand.FORWARD:
        avoidance = avoider(tank.x, tank.y, tank.angle, level)
        if avoidance is not None:
            for a_cmd in avoidance:
                tank.apply_command(a_cmd, level)
            return
    tank.apply_command(cmd, level)


def _spawn_tanks(level):
    """Create player 1 and player 2 Tank objects from level spawn points."""
    tanks = []
    for key, player_num in [("player1", 1), ("player2", 2)]:
        sp = level.spawns[key]
        tanks.append(Tank(
            sp.col * CELL_SIZE + CELL_SIZE // 2,
            sp.row * CELL_SIZE + CELL_SIZE // 2,
            FACING_TO_ANGLE[sp.facing],
            PLAYER_TANK_COLORS[player_num],
        ))
    return tanks


def _run_manual(level_path: Path, existing_screen=None, existing_assets=None):
    """Manual mode: keyboard-controlled player 1 vs AI opponent.

    Args:
        level_path: Path to the level file
        existing_screen: Existing pygame screen surface (if called from title screen)
        existing_assets: Existing AssetManager (if called from title screen)
    """
    # If called from title screen, reuse pygame initialization
    if existing_screen is None:
        pygame.init()
        screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption(WINDOW_TITLE + " [MANUAL vs AI]")
        standalone_mode = True
    else:
        screen = existing_screen
        pygame.display.set_caption(WINDOW_TITLE + " [MANUAL vs AI]")
        standalone_mode = False

    clock = pygame.time.Clock()

    if existing_assets is None:
        asset_mgr = AssetManager()
        asset_mgr.load_all()
    else:
        asset_mgr = existing_assets

    current_level = load_level(level_path)
    renderer = LevelRenderer(screen, asset_mgr)
    game_state = GameState()
    tanks = _spawn_tanks(current_level)

    # Set up game state for AI
    game_state.phase = GamePhase.PLAYING
    game_state.mode = GameMode.ONE_PLAYER
    game_state.winner = None
    game_state.tick = 0
    game_state.update_tank("player1", tanks[0])
    game_state.update_tank("player2", tanks[1])

    # Start AI opponent
    ai_queue = Queue()
    ai_controller = AIController(ai_queue, game_state, level=current_level)
    ai_thread = threading.Thread(target=ai_controller.start, daemon=True)
    ai_thread.start()

    running = True
    game_over = False
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_RETURN and game_over:
                    # Return to title screen
                    running = False
                elif event.key == pygame.K_g:
                    renderer.show_grid = not renderer.show_grid
                elif event.key == pygame.K_c:
                    renderer.show_collision = not renderer.show_collision

        if not game_over:
            # Player 1 keyboard input
            keys = pygame.key.get_pressed()
            tanks[0].handle_input(keys, current_level)

            # Process AI commands for player 2
            while True:
                try:
                    cmd = ai_queue.get_nowait()
                    tanks[1].apply_command(cmd, current_level)
                except Empty:
                    break

            # Update bullets
            for t in tanks:
                t.update_bullets(current_level)

            # Check collisions
            check_bullet_tank_collisions(tanks)

            # Check for winner
            if not tanks[0].alive or not tanks[1].alive:
                game_over = True
                winner = tanks[0].color if tanks[0].alive else tanks[1].color
                game_state.winner = winner
                game_state.phase = GamePhase.GAME_OVER
                ai_controller.stop()

            # Update game state for AI
            game_state.tick += 1
            game_state.update_tank("player1", tanks[0])
            game_state.update_tank("player2", tanks[1])

        # Render
        renderer.render(current_level, tanks)
        if game_over:
            renderer.render_game_over(game_state.winner or "???")

        pygame.display.flip()
        clock.tick(FPS)

    ai_controller.stop()

    # Only quit pygame if running standalone (not from title screen)
    if standalone_mode:
        pygame.quit()


def _run_game(level_path: Path):
    """Main game mode: title screen -> 1P/2P via API."""
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption(WINDOW_TITLE)
    clock = pygame.time.Clock()

    asset_mgr = AssetManager()
    asset_mgr.load_all()

    current_level = load_level(level_path)
    renderer = LevelRenderer(screen, asset_mgr)
    game_state = GameState()
    game_history = GameHistory()

    phase = GamePhase.TITLE_SCREEN
    selected_index = 0
    tanks = []
    ai_controller = None
    demo_controller = None
    api_started = False
    p1_avoider = ObstacleAvoider()
    p2_avoider = ObstacleAvoider()
    p1_auto_shoot = False
    p2_auto_shoot = False
    p1_executor = None
    p2_executor = None

    # Queues
    p1_queue = Queue()
    p2_queue = Queue()
    ai_queue = Queue()

    def start_game(mode: GameMode):
        nonlocal phase, tanks, ai_controller, demo_controller, api_started
        nonlocal p1_queue, p2_queue, ai_queue
        nonlocal p1_avoider, p2_avoider
        nonlocal p1_auto_shoot, p2_auto_shoot
        nonlocal p1_executor, p2_executor

        # Fresh queues
        p1_queue = Queue()
        p2_queue = Queue()
        ai_queue = Queue()

        # Fresh avoiders for the new round
        p1_avoider = ObstacleAvoider()
        p2_avoider = ObstacleAvoider()
        p1_auto_shoot = False
        p2_auto_shoot = False
        p1_executor = None
        p2_executor = None
        game_state.set_strategy("player1", None)
        game_state.set_strategy("player2", None)

        tanks = _spawn_tanks(current_level)

        game_state.phase = GamePhase.PLAYING
        game_state.mode = mode
        game_state.winner = None
        game_state.tick = 0

        # Seed initial tank state so demo/AI can read positions immediately
        game_state.update_tank("player1", tanks[0])
        game_state.update_tank("player2", tanks[1])

        # Start API server once (skip for demo mode)
        if not api_started and mode != GameMode.DEMO:
            p2_api_q = p2_queue if mode == GameMode.TWO_PLAYER else None
            api_thread = threading.Thread(
                target=run_tank_api,
                args=(p1_queue, p2_api_q, game_state, game_history, API_HOST, API_PORT),
                daemon=True,
            )
            api_thread.start()
            api_started = True

        # Start AI for 1-player mode
        if mode == GameMode.ONE_PLAYER:
            ai_controller = AIController(ai_queue, game_state,
                                         level=current_level)
            ai_thread = threading.Thread(target=ai_controller.start, daemon=True)
            ai_thread.start()
        else:
            ai_controller = None

        # Start demo controller
        if mode == GameMode.DEMO:
            demo_controller = DemoController(p1_queue, p2_queue, game_state,
                                             level=current_level)
            demo_thread = threading.Thread(target=demo_controller.start, daemon=True)
            demo_thread.start()
        else:
            demo_controller = None

        phase = GamePhase.PLAYING

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if phase == GamePhase.PLAYING or phase == GamePhase.GAME_OVER:
                        # Return to title screen from gameplay or game over
                        phase = GamePhase.TITLE_SCREEN
                        game_state.phase = GamePhase.TITLE_SCREEN
                        if ai_controller:
                            ai_controller.stop()
                            ai_controller = None
                        if demo_controller:
                            demo_controller.stop()
                            demo_controller = None
                    elif phase == GamePhase.TITLE_SCREEN:
                        # Exit program only from title screen
                        running = False

                elif phase == GamePhase.TITLE_SCREEN:
                    if event.key == pygame.K_UP:
                        selected_index = (selected_index - 1) % 4
                    elif event.key == pygame.K_DOWN:
                        selected_index = (selected_index + 1) % 4
                    elif event.key == pygame.K_RETURN:
                        if selected_index == 2:
                            # Manual mode - run separate game loop
                            _run_manual(level_path, screen, asset_mgr)
                            # When manual mode exits, we return to title screen
                            # Restore title screen caption
                            pygame.display.set_caption(WINDOW_TITLE)
                        else:
                            mode_map = {
                                0: GameMode.ONE_PLAYER,
                                1: GameMode.TWO_PLAYER,
                                3: GameMode.DEMO,
                            }
                            start_game(mode_map[selected_index])

                elif phase == GamePhase.GAME_OVER:
                    if event.key == pygame.K_RETURN:
                        phase = GamePhase.TITLE_SCREEN
                        game_state.phase = GamePhase.TITLE_SCREEN

                elif phase == GamePhase.PLAYING:
                    if event.key == pygame.K_g:
                        renderer.show_grid = not renderer.show_grid
                    elif event.key == pygame.K_c:
                        renderer.show_collision = not renderer.show_collision

        # ---- Title Screen ----
        if phase == GamePhase.TITLE_SCREEN:
            renderer.render_title_screen(selected_index)

        # ---- Playing ----
        elif phase == GamePhase.PLAYING and tanks:
            # Demo: check for scenario reset request
            if demo_controller and demo_controller._request_reset:
                tanks = _spawn_tanks(current_level)
                game_state.winner = None
                game_state.tick = 0
                game_state.phase = GamePhase.PLAYING
                game_state.update_tank("player1", tanks[0])
                game_state.update_tank("player2", tanks[1])
                demo_controller._request_reset = False

            # Drain player 1 command queue (API — avoidance enabled)
            while True:
                try:
                    item = p1_queue.get_nowait()
                    if isinstance(item, tuple) and item[0] == "strategy":
                        _, text, parsed_cmds = item
                        p1_executor = CommandExecutor(level=current_level)
                        p1_executor.set_commands(parsed_cmds)
                        game_state.set_strategy("player1", text)
                        game_history.log_command(game_state.tick, "player1", text, "strategy")
                    elif isinstance(item, tuple) and item[0] == "clear_strategy":
                        p1_executor = None
                        game_state.set_strategy("player1", None)
                        game_history.log_command(game_state.tick, "player1", "stop", "strategy")
                    elif item == TankCommand.AUTO_SHOOT_ON:
                        p1_auto_shoot = True
                        game_history.log_command(game_state.tick, "player1", item.value, "direct")
                    elif item == TankCommand.AUTO_SHOOT_OFF:
                        p1_auto_shoot = False
                        game_history.log_command(game_state.tick, "player1", item.value, "direct")
                    else:
                        game_history.log_command(game_state.tick, "player1", item.value, "direct")
                        _apply_with_avoidance(tanks[0], item, current_level,
                                              p1_avoider)
                except Empty:
                    break

            # Drain player 2 / AI / demo command queue
            if game_state.mode == GameMode.DEMO:
                # Demo uses CommandExecutor which already has avoidance
                q, use_avoidance = p2_queue, False
            elif game_state.mode == GameMode.TWO_PLAYER:
                # 2-player API — avoidance enabled
                q, use_avoidance = p2_queue, True
            else:
                # AI controller already applies avoidance internally
                q, use_avoidance = ai_queue, False
            while True:
                try:
                    item = q.get_nowait()
                    if isinstance(item, tuple) and item[0] == "strategy":
                        _, text, parsed_cmds = item
                        p2_executor = CommandExecutor(level=current_level)
                        p2_executor.set_commands(parsed_cmds)
                        game_state.set_strategy("player2", text)
                        game_history.log_command(game_state.tick, "player2", text, "strategy")
                    elif isinstance(item, tuple) and item[0] == "clear_strategy":
                        p2_executor = None
                        game_state.set_strategy("player2", None)
                        game_history.log_command(game_state.tick, "player2", "stop", "strategy")
                    elif item == TankCommand.AUTO_SHOOT_ON:
                        p2_auto_shoot = True
                        game_history.log_command(game_state.tick, "player2", item.value, "direct")
                    elif item == TankCommand.AUTO_SHOOT_OFF:
                        p2_auto_shoot = False
                        game_history.log_command(game_state.tick, "player2", item.value, "direct")
                    elif use_avoidance:
                        game_history.log_command(game_state.tick, "player2", item.value, "direct")
                        _apply_with_avoidance(tanks[1], item, current_level,
                                              p2_avoider)
                    else:
                        game_history.log_command(game_state.tick, "player2", item.value, "direct")
                        tanks[1].apply_command(item, current_level)
                except Empty:
                    break

            # Tick NL executors (single snapshot for both)
            if p1_executor is not None or p2_executor is not None:
                snap = game_state.snapshot()["tanks"]
                s1 = snap.get("player1", {})
                s2 = snap.get("player2", {})
                if p1_executor is not None and tanks[0].alive:
                    for cmd in p1_executor.tick(s1, s2):
                        _apply_with_avoidance(tanks[0], cmd, current_level,
                                              p1_avoider)
                if p2_executor is not None and tanks[1].alive:
                    for cmd in p2_executor.tick(s2, s1):
                        _apply_with_avoidance(tanks[1], cmd, current_level,
                                              p2_avoider)

            # Auto-shoot: if enabled, track the enemy and fire when in FOV
            # with clear line of sight through obstacles
            if p1_auto_shoot and tanks[0].alive and tanks[1].alive:
                me_snap = {"x": tanks[0].x, "y": tanks[0].y,
                           "angle": tanks[0].angle}
                tgt_snap = {"x": tanks[1].x, "y": tanks[1].y,
                            "alive": tanks[1].alive}
                if is_in_sight(me_snap, tgt_snap, level=current_level):
                    desired = angle_to_target(tanks[0].x, tanks[0].y,
                                              tanks[1].x, tanks[1].y)
                    err = angle_error(desired, tanks[0].angle)
                    if abs(err) > 3:
                        cmd = TankCommand.ROTATE_RIGHT if err > 0 else TankCommand.ROTATE_LEFT
                        tanks[0].apply_command(cmd, current_level)
                    tanks[0].apply_command(TankCommand.SHOOT, current_level)

            if p2_auto_shoot and tanks[1].alive and tanks[0].alive:
                me_snap = {"x": tanks[1].x, "y": tanks[1].y,
                           "angle": tanks[1].angle}
                tgt_snap = {"x": tanks[0].x, "y": tanks[0].y,
                            "alive": tanks[0].alive}
                if is_in_sight(me_snap, tgt_snap, level=current_level):
                    desired = angle_to_target(tanks[1].x, tanks[1].y,
                                              tanks[0].x, tanks[0].y)
                    err = angle_error(desired, tanks[1].angle)
                    if abs(err) > 3:
                        cmd = TankCommand.ROTATE_RIGHT if err > 0 else TankCommand.ROTATE_LEFT
                        tanks[1].apply_command(cmd, current_level)
                    tanks[1].apply_command(TankCommand.SHOOT, current_level)

            # Update bullets
            for t in tanks:
                t.update_bullets(current_level)

            # Bullet-tank collisions
            check_bullet_tank_collisions(tanks)

            # Check win condition
            for t in tanks:
                if not t.alive:
                    if game_state.mode == GameMode.DEMO:
                        # In demo, auto-reset for next scenario
                        if demo_controller:
                            demo_controller._request_reset = True
                        break
                    winners = [other for other in tanks if other.alive]
                    game_state.winner = winners[0].color if winners else None
                    phase = GamePhase.GAME_OVER
                    game_state.phase = GamePhase.GAME_OVER
                    if ai_controller:
                        ai_controller.stop()
                        ai_controller = None
                    break

            # Update shared state for API/AI/demo reads
            game_state.tick += 1
            game_state.update_tank("player1", tanks[0])
            game_state.update_tank("player2", tanks[1])

            # Log periodic snapshots every ~5 seconds (150 frames at 30 FPS)
            if game_history.should_snapshot(game_state.tick):
                game_history.log_snapshot(game_state.tick, game_state.snapshot())

            # Render
            renderer.render(current_level, tanks)

            # Demo overlay
            if demo_controller and game_state.mode == GameMode.DEMO:
                renderer.render_demo_overlay(
                    demo_controller.scenario_display,
                    demo_controller.current_scenario_index,
                    len(DEMO_SCENARIOS),
                )

        # ---- Game Over ----
        elif phase == GamePhase.GAME_OVER:
            renderer.render(current_level, tanks)
            renderer.render_game_over(game_state.winner or "???")

        pygame.display.flip()
        clock.tick(FPS)

    if ai_controller:
        ai_controller.stop()
    if demo_controller:
        demo_controller.stop()
    pygame.quit()


def main():
    args = sys.argv[1:]
    manual = "--manual" in args
    args = [a for a in args if a != "--manual"]
    level_path = Path(args[0]) if args else LEVELS_DIR / "default.json"

    if not level_path.exists():
        print(f"Level file not found: {level_path}")
        sys.exit(1)

    if manual:
        _run_manual(level_path)
    else:
        _run_game(level_path)


if __name__ == "__main__":
    main()
