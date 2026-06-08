"""
Air Hockey Vision - Game Screen
Soccer-pitch layout with live camera panels on left + right sides.
"""

import math
import random
import time
import cv2
import pygame

from src.core.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    TARGET_FPS, CAMERA_PREVIEW_FPS,
    TABLE_LEFT, TABLE_RIGHT, TABLE_TOP, TABLE_BOTTOM,
    TABLE_CENTER_X, TABLE_CENTER_Y,
    GOAL_SIZE, GOAL_HALF,
    CAM_PANEL_W, CAM_PANEL_H,
    C_PADDLE_P1, C_PADDLE_P2, C_PADDLE_AI,
    C_GOAL_GLOW_P1, C_GOAL_GLOW_P2,
    C_WHITE, C_UI_DIM, C_BACKGROUND,
    C_FIELD_LIGHT, C_NEON_YELLOW, C_NEON_CYAN,
    SCORE_TO_WIN, MATCH_DURATION,
    MODE_VS_AI, MODE_TWO_PLAYER, MODE_TRAINING, MODE_CHALLENGE,
    STATE_MAIN_MENU, STATE_PAUSE,
    AI_DIFFICULTY_MEDIUM,
    FONT_HUGE, FONT_LARGE, FONT_MEDIUM, FONT_SMALL, FONT_TINY,
    SENSITIVITY,
)
from src.physics.puck      import Puck
from src.physics.paddle    import Paddle
from src.physics.collision import CollisionSystem
from src.ai.ai_paddle      import AIPaddle
from src.rendering.renderer import Renderer
from src.rendering.ui       import (
    ScoreDisplay, FontCache, render_text, render_text_glow,
    draw_tracking_indicator, draw_fps,
)
from src.rendering.effects  import ParticleSystem, ScreenFlash, ScreenShake
from src.utils.replay       import ReplayRecorder
from src.core.events        import bus, EVT_PUCK_HIT_WALL, EVT_PUCK_HIT_PADDLE




class GameScreen:
    GOAL_DELAY    = 2.5
    COUNTDOWN_DUR = 3

    def __init__(self, surface: pygame.Surface, sound_manager,
                 hand_tracker, config: dict, stats: dict, settings_state: dict):
        self.surface  = surface
        self.sound    = sound_manager
        self.tracker  = hand_tracker
        self.config   = config
        self.stats    = stats
        self.settings_state = settings_state

        self.mode       = config.get('mode', MODE_VS_AI)
        self.diff_level = config.get('difficulty', AI_DIFFICULTY_MEDIUM)

        # Physics
        self.puck      = Puck()
        self.paddle1   = Paddle(1, C_PADDLE_P1)
        self.paddle2   = Paddle(2, C_PADDLE_P2 if self.mode == MODE_TWO_PLAYER
                                    else C_PADDLE_AI)
        self.collision = CollisionSystem()

        # AI
        self._ai: AIPaddle | None = None
        if self.mode != MODE_TWO_PLAYER:
            self._ai = AIPaddle(self.paddle2, self.diff_level)

        # Scoring
        self.p1_score  = 0
        self.p2_score  = 0
        self._time_start   = time.perf_counter()
        self._time_elapsed = 0.0
        self._match_over   = False

        # Rendering
        self.renderer   = Renderer(surface, self.settings_state)
        self.score_disp = ScoreDisplay(C_GOAL_GLOW_P1, C_GOAL_GLOW_P2)

        # Goal state
        self._goal_state    = None
        self._goal_timer    = 0.0
        self._goal_flash_p1 = 0.0
        self._goal_flash_p2 = 0.0
        self._goal_spark_timer = 0.0

        # Screen shake (haptic feedback)
        self._screen_shake = ScreenShake()
        self._shake_surf: pygame.Surface | None = None

        # Countdown
        self._counting_down  = True
        self._countdown      = self.COUNTDOWN_DUR
        self._countdown_start= time.perf_counter()

        # Stats
        self._rally_timer  = 0.0
        self._max_rally    = 0.0
        self._fastest_puck = 0.0
        self._match_point_played = False

        # Replay
        self._replay = ReplayRecorder()

        # Keyboard speed
        self._kb_speed = 9.0

        # Events
        bus.subscribe(EVT_PUCK_HIT_WALL,   self._on_wall_hit)
        bus.subscribe(EVT_PUCK_HIT_PADDLE, self._on_paddle_hit)

        # Camera surface cache
        self._cam_surf1: pygame.Surface | None = None
        self._cam_surf2 = pygame.Surface((CAM_PANEL_W, CAM_PANEL_H))
        self._panel_bg = pygame.Surface((CAM_PANEL_W, CAM_PANEL_H), pygame.SRCALPHA)
        self._panel_bg.fill((0, 0, 0, 200))
        self._glass_cache: dict[tuple, pygame.Surface] = {}
        self._ai_panel_bg = self._build_ai_panel_bg()
        self._last_hand_smooth: float | None = None

        self._ai_avatar = None

        self._cam_update_every = max(1, round(TARGET_FPS / max(1, CAMERA_PREVIEW_FPS)))
        self._cam_frame_count  = 0

        self.puck.reset(serve_to=1)
        self.puck.active = False

    def _build_ai_panel_bg(self) -> pygame.Surface:
        surf = pygame.Surface((CAM_PANEL_W, CAM_PANEL_H), pygame.SRCALPHA)
        for row in range(CAM_PANEL_H):
            alpha = int(160 + 60 * row / CAM_PANEL_H)
            t = row / CAM_PANEL_H
            r = int(30 + 20 * t)
            g = int(0 + 5 * t)
            b = int(40 + 30 * t)
            pygame.draw.line(surf, (r, g, b, alpha), (0, row), (CAM_PANEL_W, row))
        return surf

    def _glass_overlay(self, color) -> pygame.Surface:
        key = tuple(color[:3])
        glass = self._glass_cache.get(key)
        if glass is None:
            glass = pygame.Surface((CAM_PANEL_W, 24), pygame.SRCALPHA)
            glass.fill((*key, 30))
            self._glass_cache[key] = glass
        return glass

    # ── Public API ────────────────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return STATE_PAUSE
            if event.key == pygame.K_r and self._match_over:
                self._restart()
        return None

    def update(self, dt: float, mouse_pos, mouse_down: bool) -> str | None:
        now = time.perf_counter()

        smooth = float(self.settings_state.get('hand_smooth', 0.55))
        if smooth != self._last_hand_smooth:
            self.tracker.set_smoothing(smooth)
            self._last_hand_smooth = smooth

        # Camera thumbnails update at a capped rate, and can be disabled.
        self._cam_frame_count += 1
        if not self.settings_state.get('show_camera', True):
            self._cam_surf1 = None
            self._cam_surf2 = None
        elif self._cam_frame_count % self._cam_update_every == 0:
            self._update_camera_surfaces()

        # Countdown
        if self._counting_down:
            elapsed = now - self._countdown_start
            cd = self.COUNTDOWN_DUR - int(elapsed)
            if cd != self._countdown:
                self._countdown = cd
                if cd > 0:
                    self.sound.play_countdown()
            if elapsed >= self.COUNTDOWN_DUR:
                self._counting_down = False
                self.puck.active    = True
            return None

        if self._match_over:
            return None

        # Timer
        if MATCH_DURATION > 0:
            self._time_elapsed = now - self._time_start
            if self._time_elapsed >= MATCH_DURATION:
                self._end_match()
                return None

        # Goal delay
        if self._goal_state:
            self._goal_timer    += dt
            self._goal_flash_p1  = max(0.0, self._goal_flash_p1 - dt * 1.5)
            self._goal_flash_p2  = max(0.0, self._goal_flash_p2 - dt * 1.5)

            # Continuous mini celebration sparks during goal banner
            self._goal_spark_timer += dt
            if self._goal_spark_timer >= 0.055:
                self._goal_spark_timer = 0.0
                color = C_GOAL_GLOW_P1 if self._goal_state == 'p1' else C_GOAL_GLOW_P2
                cx, cy = TABLE_CENTER_X, TABLE_CENTER_Y
                for _ in range(2):
                    sx = cx + random.randint(-200, 200)
                    sy = cy + random.randint(-50, 30)
                    self.renderer.particles.spawn_hit_sparks(sx, sy, color, count=3)

            if self._goal_timer >= self.GOAL_DELAY:
                self._goal_state = None
                self._goal_timer = 0.0
                self._goal_spark_timer = 0.0
                self._serve_puck()
            return None

        # Move paddles
        self._update_paddles(dt)

        # Animate puck drop-in
        if hasattr(self.puck, 'spawn_scale') and self.puck.spawn_scale > 1.0:
            self.puck.spawn_scale = max(1.0, self.puck.spawn_scale - dt * 6.0)
            self.puck.x = float(TABLE_CENTER_X)
            self.puck.y = float(TABLE_CENTER_Y)

        # AI
        if self._ai:
            self._ai.update(self.puck, dt)
            self._ai.adapt_score(self.p2_score, self.p1_score)

        # Friction
        self.puck.vx *= 0.999
        self.puck.vy *= 0.999

        # Physics
        goal = self.collision.update(self.puck, [self.paddle1, self.paddle2])

        # Trail update
        self.puck.trail.append((self.puck.x, self.puck.y))
        if len(self.puck.trail) > 16:
            self.puck.trail.pop(0)
        self.puck.spin += self.puck.speed * 1.5

        # Stats
        spd = self.puck.speed
        if spd > self._fastest_puck:
            self._fastest_puck = spd
        if spd > 1.0:
            self._rally_timer += dt
            if self._rally_timer > self._max_rally:
                self._max_rally = self._rally_timer
        else:
            self._rally_timer = 0.0

        if goal:
            self._handle_goal(goal)

        self.score_disp.update()
        self.renderer.flash.update()

        return None

    def draw(self, fps: float = 60.0):
        shake_x, shake_y = self._screen_shake.update()

        if shake_x != 0 or shake_y != 0:
            # Render game to a temp surface, then blit with offset for shake effect
            w, h = self.surface.get_size()
            if self._shake_surf is None or self._shake_surf.get_size() != (w, h):
                self._shake_surf = pygame.Surface((w, h))
            orig = self.surface
            self.surface = self._shake_surf
            self.renderer.surface = self._shake_surf
            self._do_draw(fps)
            orig.fill(self.renderer.c_bg)
            orig.blit(self._shake_surf, (shake_x, shake_y))
            self.surface = orig
            self.renderer.surface = orig
        else:
            self._do_draw(fps)

    def _do_draw(self, fps: float = 60.0):
        self.renderer.clear()
        self.renderer.draw_field()
        self.renderer.draw_goal_glow(self._goal_flash_p1, self._goal_flash_p2)

        if self.puck.active:
            self.renderer.draw_puck(self.puck)

        self.renderer.draw_paddle(self.paddle1, is_ai=False)
        self.renderer.draw_paddle(self.paddle2, is_ai=(self.mode != MODE_TWO_PLAYER))

        self.renderer.draw_particles()

        # Camera panels
        self._draw_camera_panels()

        # Score bar + HUD
        self.renderer.draw_score_bar()
        self.score_disp.draw(self.surface, self.p1_score, self.p2_score,
                             None, self.mode)

        self._draw_hud(fps)
        self._draw_overlay()
        self.renderer.draw_flash()

    # ── Camera panels ─────────────────────────────────────────────────────────

    def _update_camera_surfaces(self):
        """Convert pre-rendered OpenCV thumbnail buffer to pygame surfaces."""
        thumb_bytes = self.tracker.get_thumbnail_bytes()
        if thumb_bytes is None:
            return

        tw, th = CAM_PANEL_W, CAM_PANEL_H
        try:
            surf = pygame.image.frombuffer(thumb_bytes, (tw, th), "RGB").convert()
            # P1 gets normal feed; P2/AI gets mirrored (same camera, flipped)
            self._cam_surf1 = surf
            self._cam_surf2 = pygame.transform.flip(surf, True, False)
        except Exception:
            pass

    def _draw_camera_panels(self):
        """Draw camera thumbnails in the bottom corners."""
        panel_h = CAM_PANEL_H
        panel_w = CAM_PANEL_W
        y = WINDOW_HEIGHT - panel_h - 4
        preview_on = self.settings_state.get('show_camera', True)

        # Left panel → Player 1 camera
        lx = 4
        self._draw_one_panel(lx, y, self._cam_surf1 if preview_on else None,
                             "P1", C_PADDLE_P1,
                             self.tracker.is_tracking[0], is_ai=False,
                             preview_off=not preview_on)

        # Right panel → Player 2 / AI
        rx = WINDOW_WIDTH - panel_w - 4
        label2 = "AI" if self.mode == MODE_VS_AI else "P2"
        is_ai  = (self.mode == MODE_VS_AI)

        cam2 = None if is_ai or not preview_on else self._cam_surf2
        tracking2 = self.tracker.is_tracking[1] if not is_ai else True

        self._draw_one_panel(rx, y, cam2,
                             label2, C_PADDLE_P2,
                             tracking2, is_ai=is_ai,
                             preview_off=(not preview_on and not is_ai))

    def _draw_one_panel(self, x: int, y: int, cam_surf,
                         label: str, color, is_active: bool, is_ai: bool = False,
                         preview_off: bool = False):
        """Draw one camera thumbnail panel with border and label."""
        tw, th = CAM_PANEL_W, CAM_PANEL_H

        # Background
        self.surface.blit(self._panel_bg, (x, y))

        if cam_surf:
            self.surface.blit(cam_surf, (x, y))
        elif is_ai:
            # Stylish AI panel - gradient dark background with "AI" text
            self.surface.blit(self._ai_panel_bg, (x, y))

            # Pulsing AI text
            pulse = abs(math.sin(time.perf_counter() * 2.0))
            ai_color = (
                int(color[0] * (0.6 + 0.4 * pulse)),
                int(color[1] * (0.6 + 0.4 * pulse)),
                int(color[2] * (0.6 + 0.4 * pulse)),
            )
            ai_font = FontCache.get(FONT_LARGE, bold=True)
            ai_surf = ai_font.render("AI", True, ai_color)
            ai_rect = ai_surf.get_rect(center=(x + tw // 2, y + th // 2 - 8))
            self.surface.blit(ai_surf, ai_rect)

            # Subtitle
            sub_font = FontCache.get(FONT_TINY)
            sub_surf = sub_font.render("COMPUTER", True, (*color[:3], 160))
            sub_rect = sub_surf.get_rect(center=(x + tw // 2, y + th // 2 + 22))
            self.surface.blit(sub_surf, sub_rect)
        else:
            # No camera placeholder
            pygame.draw.rect(self.surface, (20, 20, 30), (x, y, tw, th))
            font = FontCache.get(FONT_TINY)
            msg = "PREVIEW OFF" if preview_off else "NO SIGNAL"
            t    = font.render(msg, True, C_UI_DIM)
            self.surface.blit(t, t.get_rect(center=(x + tw // 2, y + th // 2)))

        # Glassmorphism overlay on top edge
        self.surface.blit(self._glass_overlay(color), (x, y))

        # Status dot (live indicator)
        dot_color = (0, 230, 80) if is_active else (200, 50, 50)
        pygame.draw.circle(self.surface, (0, 0, 0), (x + tw - 10, y + 10), 7)
        pygame.draw.circle(self.surface, dot_color, (x + tw - 10, y + 10), 5)

        # LIVE label
        live_font = FontCache.get(FONT_TINY)
        live_text = "● LIVE" if is_active else "● OFF"
        live_color = (0, 230, 80) if is_active else (200, 50, 50)
        live_surf = live_font.render(live_text, True, live_color)
        self.surface.blit(live_surf, (x + 5, y + 4))

        # Border with player color + rounded, sleeker
        pygame.draw.rect(self.surface, color, (x, y, tw, th), 2, border_radius=6)
        
        # Inner thin border for professional look
        pygame.draw.rect(self.surface, (255, 255, 255, 60), (x+2, y+2, tw-4, th-4), 1, border_radius=4)

        # Label below panel
        font  = FontCache.get(FONT_SMALL, bold=True)
        lsurf = font.render(label, True, color)
        self.surface.blit(lsurf, lsurf.get_rect(
            centerx=x + tw // 2, top=y + th + 4
        ))

    # ── Paddle control ────────────────────────────────────────────────────────

    def _map_camera_to_table(self, cam_x: float, cam_y: float, player_id: int) -> tuple[float, float]:
        """
        Maps an active zone of the camera to the full table.
        Uses a dynamic deadzone and smoother curve to eliminate jitter.
        """
        sensitivity = self.settings_state.get('sensitivity', 0.6)
        # Less aggressive range, min 0.4 to avoid amplifying jitter
        active_range = max(0.4, 1.0 - sensitivity * 0.5)
        active_min   = 0.5 - active_range / 2.0

        # Normalize into [0, 1] within the active zone
        nx = max(0.0, min(1.0, (cam_x - active_min) / active_range))
        ny = max(0.0, min(1.0, (cam_y - active_min) / active_range))

        # Smoother ease-in-out:
        nx = nx * nx * (3.0 - 2.0 * nx)
        ny = ny * ny * (3.0 - 2.0 * ny)

        if player_id == 1:
            tx = TABLE_LEFT + nx * (TABLE_CENTER_X - TABLE_LEFT)
        else:
            tx = TABLE_CENTER_X + nx * (TABLE_RIGHT - TABLE_CENTER_X)

        ty = TABLE_TOP + ny * (TABLE_BOTTOM - TABLE_TOP)
        return tx, ty

    def _update_paddles(self, dt: float):
        """
        Move paddles using velocity-predicted positions for zero perceptual lag.

        get_predicted_position() extrapolates one frame ahead using the current
        velocity estimate, effectively cancelling the camera → processing → game
        pipeline delay.  It feels exactly like a mouse.
        """
        # ── Player 1 (Left half) – hand index 0 ──────────────────────────────
        if self.tracker.camera_available:
            # Use predicted position to cancel pipeline latency (boosted by 1.5x for webcam lag)
            p1_pos = self.tracker.get_predicted_position(0, lookahead=dt * 1.5)
        else:
            p1_pos = None

        if p1_pos and self.tracker.is_open[0]:
            tx, ty = self._map_camera_to_table(p1_pos[0], p1_pos[1], 1)
            self.paddle1.move_to(tx, ty)
        elif not p1_pos:
            keys = pygame.key.get_pressed()
            nx, ny = self.paddle1.x, self.paddle1.y
            spd = self._kb_speed
            if keys[pygame.K_LEFT]  or keys[pygame.K_a]: nx -= spd
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]: nx += spd
            if keys[pygame.K_UP]    or keys[pygame.K_w]: ny -= spd
            if keys[pygame.K_DOWN]  or keys[pygame.K_s]: ny += spd
            self.paddle1.move_to(nx, ny)

        # ── Player 2 (Right half) – hand index 1 ─────────────────────────────
        if self.mode == MODE_TWO_PLAYER:
            if self.tracker.camera_available:
                p2_pos = self.tracker.get_predicted_position(1, lookahead=dt)
            else:
                p2_pos = None
            if p2_pos and self.tracker.is_open[1]:
                tx, ty = self._map_camera_to_table(p2_pos[0], p2_pos[1], 2)
                self.paddle2.move_to(tx, ty)

    # ── Goal handling ─────────────────────────────────────────────────────────

    def _handle_goal(self, scored_by: str):
        self._goal_state = scored_by
        self._goal_timer = 0.0

        if scored_by == 'p1':
            self.p1_score += 1
            self.score_disp.flash_p1()
            self._goal_flash_p1 = 1.0
            self.renderer.particles.spawn_goal_explosion(
                TABLE_RIGHT - 20, TABLE_CENTER_Y, 1)
            # Extra score-area burst + score number area sparks
            self.renderer.particles.spawn_score_burst(
                TABLE_CENTER_X - 100, 40, C_GOAL_GLOW_P1, count=22)
            self.renderer.flash.trigger(C_GOAL_GLOW_P1, 120)
            self._screen_shake.trigger(amplitude=10, frames=18)
        else:
            self.p2_score += 1
            self.score_disp.flash_p2()
            self._goal_flash_p2 = 1.0
            self.renderer.particles.spawn_goal_explosion(
                TABLE_LEFT + 20, TABLE_CENTER_Y, 2)
            self.renderer.particles.spawn_score_burst(
                TABLE_CENTER_X + 100, 40, C_GOAL_GLOW_P2, count=22)
            self.renderer.flash.trigger(C_GOAL_GLOW_P2, 120)
            self._screen_shake.trigger(amplitude=10, frames=18)

        self.sound.play_goal()
        self.puck.active = False
        self.stats['total_goals'] = self.stats.get('total_goals', 0) + 1

        if self.p1_score >= SCORE_TO_WIN or self.p2_score >= SCORE_TO_WIN:
            self._end_match()

    def _serve_puck(self):
        serve_to = 2 if self._goal_state == 'p1' else 1
        self.puck.reset(serve_to=serve_to)
        self._counting_down   = True
        self._countdown       = self.COUNTDOWN_DUR
        self._countdown_start = time.perf_counter()

        # Match point hype
        if self.p1_score == SCORE_TO_WIN - 1 or self.p2_score == SCORE_TO_WIN - 1:
            if not getattr(self, '_match_point_played', False):
                self.sound.play_goal()  # Extra sound for hype
                self.renderer.flash.trigger(C_NEON_YELLOW, 200)
                self._match_point_played = True

    def _end_match(self):
        self._match_over = True
        self.puck.active = False
        self.sound.play_game_over()

        self.stats['games_played'] = self.stats.get('games_played', 0) + 1
        if self.p1_score > self.p2_score:
            self.stats['p1_wins'] = self.stats.get('p1_wins', 0) + 1
        else:
            self.stats['p2_wins'] = self.stats.get('p2_wins', 0) + 1
        self.stats['longest_rally'] = max(
            self.stats.get('longest_rally', 0), int(self._max_rally))
        self.stats['fastest_puck'] = max(
            self.stats.get('fastest_puck', 0.0), round(self._fastest_puck, 1))

    def _restart(self):
        self.p1_score = 0
        self.p2_score = 0
        self._match_over    = False
        self._time_start    = time.perf_counter()
        self._time_elapsed  = 0.0
        self._goal_state    = None
        self._rally_timer   = 0.0
        self._max_rally     = 0.0
        self._fastest_puck  = 0.0
        self._match_point_played = False
        self.puck.reset(serve_to=1)
        self.renderer.particles.clear()
        self._counting_down   = True
        self._countdown       = self.COUNTDOWN_DUR
        self._countdown_start = time.perf_counter()

    # ── Event callbacks ───────────────────────────────────────────────────────

    def _on_wall_hit(self, **kw):
        self.sound.play_wall_hit(min(1.0, self.puck.speed / 10))
        from src.core.settings import C_PUCK
        self.renderer.particles.spawn_hit_sparks(
            self.puck.x, self.puck.y, C_PUCK, 6)

    def _on_paddle_hit(self, **kw):
        pid   = kw.get('paddle_id', 1)
        color = C_PADDLE_P1 if pid == 1 else C_PADDLE_P2
        self.sound.play_paddle_hit(min(1.0, self.puck.speed / 10))
        self.renderer.particles.spawn_hit_sparks(
            self.puck.x, self.puck.y, color, 14)

    # ── HUD + overlays ────────────────────────────────────────────────────────

    def _draw_hud(self, fps: float):
        # Keyboard hint when no hand tracking
        if not (self.tracker.camera_available and self.tracker.is_tracking[0]):
            hint = FontCache.get(FONT_TINY).render(
                "WASD / Arrow Keys — move paddle", True, C_UI_DIM)
            self.surface.blit(hint,
                hint.get_rect(centerx=TABLE_CENTER_X, bottom=TABLE_BOTTOM - 4))

    def _draw_overlay(self):
        cx = TABLE_CENTER_X
        cy = TABLE_CENTER_Y

        # Countdown
        if self._counting_down:
            cd  = max(1, self._countdown)
            txt = str(cd) if cd > 0 else "GO!"
            f   = FontCache.get(FONT_HUGE, bold=True)
            # semi-transparent background circle
            s = pygame.Surface((160, 160), pygame.SRCALPHA)
            pygame.draw.circle(s, (0, 0, 0, 140), (80, 80), 80)
            self.surface.blit(s, (cx - 80, cy - 80))
            render_text(self.surface, txt, f, C_NEON_YELLOW, (cx, cy))
            
            # Match point text
            if self.p1_score == SCORE_TO_WIN - 1 or self.p2_score == SCORE_TO_WIN - 1:
                render_text_glow(self.surface, "MATCH POINT", FontCache.get(FONT_LARGE, bold=True), C_NEON_YELLOW, (cx, cy + 120), glow_color=(255, 200, 0, 150))
            return

        # Goal banner
        if self._goal_state:
            color  = C_GOAL_GLOW_P1 if self._goal_state == 'p1' else C_GOAL_GLOW_P2
            scorer = ("PLAYER 1" if self._goal_state == 'p1'
                      else ("AI" if self.mode == MODE_VS_AI else "PLAYER 2"))

            # Shake the banner text during the first half of the delay
            shake_t = max(0.0, 1.0 - self._goal_timer / (self.GOAL_DELAY * 0.4))
            bx_off  = int(random.uniform(-3, 3) * shake_t)
            by_off  = int(random.uniform(-2, 2) * shake_t)

            # Translucent banner (taller to give subtitle breathing room)
            bw, bh = 460, 112
            ban = pygame.Surface((bw, bh), pygame.SRCALPHA)
            ban.fill((0, 0, 0, 175))
            bx = cx - bw // 2 + bx_off
            by = cy - 60 + by_off
            self.surface.blit(ban, (bx, by))
            pygame.draw.rect(self.surface, color, (bx, by, bw, bh), 2, border_radius=8)

            # Inner glow border (subtle)
            glow_c = (*color[:3], 60)
            inner_s = pygame.Surface((bw - 4, bh - 4), pygame.SRCALPHA)
            pygame.draw.rect(inner_s, glow_c, inner_s.get_rect(), 4, border_radius=6)
            self.surface.blit(inner_s, (bx + 2, by + 2))

            # "GOAL!" text — centred vertically in top 60% of banner
            render_text(self.surface, "GOAL!",
                        FontCache.get(FONT_LARGE, bold=True), color,
                        (cx + bx_off, by + 42), shadow=True)

            # Subtitle — centred in bottom 40%, well clear of border
            render_text(self.surface, f"{scorer} SCORES",
                        FontCache.get(FONT_SMALL), color,
                        (cx + bx_off, by + bh - 26))
            return

        # Match over
        if self._match_over:
            if self.p1_score > self.p2_score:
                wtxt, wcolor = "PLAYER 1 WINS!", C_GOAL_GLOW_P1
            elif self.p2_score > self.p1_score:
                w = "AI WINS!" if self.mode == MODE_VS_AI else "PLAYER 2 WINS!"
                wtxt, wcolor = w, C_GOAL_GLOW_P2
            else:
                wtxt, wcolor = "DRAW!", C_NEON_YELLOW

            bw, bh = 520, 170
            ban = pygame.Surface((bw, bh), pygame.SRCALPHA)
            ban.fill((0, 0, 0, 200))
            self.surface.blit(ban, (cx - bw // 2, cy - 90))
            pygame.draw.rect(self.surface, wcolor,
                             (cx - bw // 2, cy - 90, bw, bh), 2, border_radius=8)

            render_text(self.surface, wtxt,
                        FontCache.get(FONT_LARGE, bold=True), wcolor,
                        (cx, cy - 50), shadow=True)
            render_text(self.surface, f"{self.p1_score}  :  {self.p2_score}",
                        FontCache.get(FONT_HUGE, bold=True), C_WHITE,
                        (cx, cy + 10))
            render_text(self.surface, "Press R to restart  •  ESC for menu",
                        FontCache.get(FONT_TINY), C_UI_DIM,
                        (cx, cy + 72))

    def cleanup(self):
        bus.unsubscribe(EVT_PUCK_HIT_WALL,   self._on_wall_hit)
        bus.unsubscribe(EVT_PUCK_HIT_PADDLE, self._on_paddle_hit)
