"""
Air Hockey Vision - Main Game Controller
Top-level state machine connecting all screens.
"""

import sys
import time
import pygame

from src.core.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE, TARGET_FPS,
    MAX_FRAME_DT,
    STATE_MAIN_MENU, STATE_GAME, STATE_SETTINGS, STATE_STATS, STATE_PAUSE,
    MODE_VS_AI, AI_DIFFICULTY_MEDIUM, CAMERA_INDEX,
)
from src.audio.sound_manager    import SoundManager
from src.vision.hand_tracker    import HandTracker
from src.screens.main_menu      import MainMenu
from src.screens.game_screen    import GameScreen
from src.screens.pause_menu     import PauseMenu
from src.screens.settings_screen import SettingsScreen
from src.screens.stats_screen   import StatsScreen


class Game:
    """
    Top-level application.
    Owns the pygame window, clock, and orchestrates state transitions.
    """

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode(
            (WINDOW_WIDTH, WINDOW_HEIGHT),
            pygame.HWSURFACE | pygame.DOUBLEBUF,
        )
        pygame.display.set_caption(WINDOW_TITLE)

        # Try to set a nice icon
        try:
            icon = pygame.Surface((32, 32), pygame.SRCALPHA)
            # Subtle cyan neon glow background
            for r in range(15, 9, -2):
                alpha = int(45 * (1.0 - (r - 10) / 6))
                pygame.draw.circle(icon, (0, 220, 255, alpha), (16, 16), r)
            # Sleek cyan outer ring
            pygame.draw.circle(icon, (0, 220, 255), (16, 16), 11, 2)
            # Metallic puck body
            pygame.draw.circle(icon, (40, 44, 55), (16, 16), 9)
            # Silver inner ridge
            pygame.draw.circle(icon, (180, 185, 200), (16, 16), 7, 1)
            # Bright highlight shine (3D effect)
            pygame.draw.circle(icon, (255, 255, 255), (13, 13), 2)
            pygame.display.set_icon(icon)
        except Exception:
            pass

        self.clock = pygame.time.Clock()
        self._running = True

        # ── Shared services ───────────────────────────────────────────────
        self.sound   = SoundManager()
        self.sound.init()

        self.tracker = HandTracker()
        self._tracker_started = False

        # ── Shared state / settings ───────────────────────────────────────
        self.settings_state = {
            'volume':      0.7,
            'hand_smooth': 0.55,
            'show_camera': True,
        }
        self.session_stats: dict = {
            'games_played': 0,
            'p1_wins':      0,
            'p2_wins':      0,
            'total_goals':  0,
            'longest_rally':0,
            'fastest_puck': 0.0,
        }

        # ── Screen instances ──────────────────────────────────────────────
        self._state      = STATE_MAIN_MENU
        self._prev_state = None
        self._game_config = {'mode': MODE_VS_AI, 'difficulty': AI_DIFFICULTY_MEDIUM}

        self._main_menu      = MainMenu(self.sound)
        self._game_screen: GameScreen | None = None
        self._pause_menu: PauseMenu | None   = None
        self._settings_screen = SettingsScreen(self.sound, self.settings_state)
        self._stats_screen    = StatsScreen(self.sound, self.session_stats)

        # Input state
        self._mouse_just_down = False

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self):
        print("[Game] Starting Air Hockey Vision…")
        self._start_tracker()

        while self._running:
            dt  = min(self.clock.tick(TARGET_FPS) / 1000.0, MAX_FRAME_DT)
            fps = self.clock.get_fps()

            mouse_pos  = pygame.mouse.get_pos()
            mouse_down = pygame.mouse.get_pressed()[0]

            # ── Events ────────────────────────────────────────────────────
            self._mouse_just_down = False
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F11:
                        pygame.display.toggle_fullscreen()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._mouse_just_down = True

                # Forward to active screen
                result = self._dispatch_event(event)
                if result:
                    self._transition(result, {})

            # ── Update + Draw ──────────────────────────────────────────────
            self._update_and_draw(dt, fps, mouse_pos, mouse_down)
            pygame.display.flip()

        self._shutdown()

    # ── State dispatch ────────────────────────────────────────────────────────

    def _dispatch_event(self, event) -> str | None:
        if self._state == STATE_GAME and self._game_screen:
            return self._game_screen.handle_event(event)
        return None

    def _update_and_draw(self, dt: float, fps: float,
                          mouse_pos, mouse_down: bool):
        s = self._state

        if s == STATE_MAIN_MENU:
            result = self._main_menu.update(dt, mouse_pos, mouse_down)
            self._main_menu.draw(self.screen)
            if result:
                next_s, cfg = result
                if next_s == 'quit':
                    self._running = False
                else:
                    self._transition(next_s, cfg)

        elif s == STATE_GAME:
            if self._game_screen:
                result = self._game_screen.update(dt, mouse_pos, mouse_down)
                self._game_screen.draw(fps)
                if result:
                    self._transition(result, {})

        elif s == STATE_PAUSE:
            # Draw game underneath
            if self._game_screen:
                self._game_screen.draw(fps)
            if self._pause_menu:
                result = self._pause_menu.update(dt, mouse_pos, mouse_down)
                self._pause_menu.draw(self.screen)
                if result == 'resume':
                    self._transition(STATE_GAME, {})
                elif result == 'restart':
                    self._start_new_game(self._game_config)
                elif result:
                    self._transition(result, {})

        elif s == STATE_SETTINGS:
            result = self._settings_screen.update(
                dt, mouse_pos, mouse_down, self._mouse_just_down
            )
            self._settings_screen.draw(self.screen)
            if result:
                self._transition(result, {})

        elif s == STATE_STATS:
            result = self._stats_screen.update(dt, mouse_pos, mouse_down)
            self._stats_screen.draw(self.screen)
            if result:
                self._transition(result, {})

    # ── Transitions ───────────────────────────────────────────────────────────

    def _transition(self, next_state: str, cfg: dict):
        print(f"[Game] {self._state} → {next_state}")

        if next_state == STATE_GAME:
            if cfg:
                self._game_config = cfg
            self._start_new_game(self._game_config)

        elif next_state == STATE_PAUSE:
            if self._pause_menu is None:
                self._pause_menu = PauseMenu(self.sound)

        elif next_state == STATE_MAIN_MENU:
            if self._game_screen:
                self._game_screen.cleanup()
                self._game_screen = None

        self._prev_state = self._state
        self._state      = next_state

    def _start_new_game(self, cfg: dict):
        if self._game_screen:
            self._game_screen.cleanup()
        self._game_screen = GameScreen(
            self.screen, self.sound, self.tracker,
            cfg, self.session_stats, self.settings_state
        )
        self._state = STATE_GAME

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _start_tracker(self):
        ok = self.tracker.start(CAMERA_INDEX)
        self._tracker_started = ok
        if ok:
            print("[Vision] Camera started — hand tracking active.")
        else:
            print("[Vision] Camera unavailable — keyboard fallback active.")



    def _shutdown(self):
        print("[Game] Shutting down…")
        self.tracker.stop()
        pygame.quit()
        sys.exit(0)
