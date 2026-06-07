"""
Air Hockey Vision - Main Renderer
Soccer-pitch style: green striped field, white markings, camera panels on sides.
"""

import math
import pygame

from src.core.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    TABLE_LEFT, TABLE_RIGHT, TABLE_TOP, TABLE_BOTTOM,
    TABLE_CENTER_X, TABLE_CENTER_Y, TABLE_WIDTH, TABLE_HEIGHT,
    GOAL_SIZE, GOAL_HALF,
    SCORE_BAR_TOP, SCORE_BAR_HEIGHT,
    C_BACKGROUND, C_FIELD_LIGHT, C_FIELD_DARK, C_FIELD_LINE,
    C_FIELD_NET, C_SCORE_BAR, C_SCORE_BAR2,
    C_PUCK, C_PUCK_SHADOW, C_PADDLE_P1, C_PADDLE_P2, C_PADDLE_AI,
    C_GOAL_GLOW_P1, C_GOAL_GLOW_P2, C_WHITE, C_UI_DIM,
    PUCK_RADIUS, PADDLE_RADIUS, TRAIL_LENGTH,
    THEME_NEON, THEME_SOCCER,
)
from src.rendering.effects import (
    ParticleSystem, ScreenFlash,
    draw_trail,
)


class Renderer:
    """Central rendering class — soccer-pitch aesthetic."""

    STRIPE_W = 72   # width of each vertical stripe on the pitch

    def __init__(self, surface: pygame.Surface, settings_state: dict):
        self.surface   = surface
        self.particles = ParticleSystem()
        self.flash     = ScreenFlash()
        self.settings_state = settings_state
        self._goal_glow_surfaces: dict[tuple, pygame.Surface] = {}
        
        self.theme = self.settings_state.get('theme', THEME_NEON)
        self._load_theme()

        # Pre-rendered surfaces
        self._field_surf   = self._build_field()
        self._score_bar    = self._build_score_bar()

    def _load_theme(self):
        if self.theme == THEME_SOCCER:
            self.c_bg = (30, 100, 40)       # Dark green grass
            self.c_light = (40, 120, 50)    # Light grass stripe
            self.c_dark = (35, 110, 45)     # Dark grass stripe
            self.c_line = (240, 255, 240)   # White field lines
        else:
            self.c_bg = C_BACKGROUND
            self.c_light = C_FIELD_LIGHT
            self.c_dark = C_FIELD_DARK
            self.c_line = C_FIELD_LINE

    # ── Public draw API ───────────────────────────────────────────────────────

    def clear(self):
        self.surface.fill(self.c_bg)

    def draw_field(self):
        self.surface.blit(self._field_surf, (0, 0))

    def draw_score_bar(self):
        self.surface.blit(self._score_bar, (0, SCORE_BAR_TOP))

    def draw_puck(self, puck):
        if not puck.active:
            return
        # Shadow
        shadow_r = puck.radius - 2
        pygame.draw.circle(self.surface, C_PUCK_SHADOW,
                           (int(puck.x) + 3, int(puck.y) + 3), shadow_r)
        # Trail
        draw_trail(self.surface, puck.trail, C_PUCK, max_radius=puck.radius - 4)
        # Main disc
        pygame.draw.circle(self.surface, C_PUCK,
                           (int(puck.x), int(puck.y)), puck.radius)
        # Inner ring
        pygame.draw.circle(self.surface, (180, 180, 200),
                           (int(puck.x), int(puck.y)), puck.radius - 5, 2)
        # Shine
        pygame.draw.circle(self.surface, (255, 255, 255),
                           (int(puck.x) - 4, int(puck.y) - 4), 4)

    def draw_paddle(self, paddle, is_ai: bool = False):
        color = C_PADDLE_AI if is_ai else (
            C_PADDLE_P1 if paddle.player_id == 1 else C_PADDLE_P2
        )
        cx, cy = int(paddle.x), int(paddle.y)
        r      = paddle.radius

        # Shadow
        pygame.draw.circle(self.surface, (0, 0, 0, 80),
                           (cx + 4, cy + 4), r)

        # Trail
        draw_trail(self.surface, paddle.trail, color, max_radius=r // 2)

        # Main disc - filled
        pygame.draw.circle(self.surface, color, (cx, cy), r)

        # Darker outer ring
        darker = tuple(max(0, c - 60) for c in color)
        pygame.draw.circle(self.surface, darker, (cx, cy), r, 3)

        # Inner light ring
        lighter = tuple(min(255, c + 80) for c in color)
        pygame.draw.circle(self.surface, lighter, (cx, cy), r // 2, 2)

        # Center white dot
        pygame.draw.circle(self.surface, C_WHITE, (cx, cy), 5)

        # Shine
        pygame.draw.circle(self.surface, (255, 255, 255),
                           (cx - r // 3, cy - r // 3), r // 5)

    def draw_goal_glow(self, p1_flash: float = 0.0, p2_flash: float = 0.0):
        """Pulse the goal openings when a goal is scored."""
        cy  = TABLE_CENTER_Y
        hw  = GOAL_HALF

        # Right goal (P1 scores here, cyan)
        if p1_flash > 0:
            alpha = int(80 + 150 * p1_flash)
            s = self._goal_glow_surface(C_GOAL_GLOW_P1, alpha)
            self.surface.blit(s, (TABLE_RIGHT - 4, cy - hw),
                              special_flags=pygame.BLEND_RGBA_ADD)

        # Left goal (P2 scores here, magenta)
        if p2_flash > 0:
            alpha = int(80 + 150 * p2_flash)
            s = self._goal_glow_surface(C_GOAL_GLOW_P2, alpha)
            self.surface.blit(s, (TABLE_LEFT - 4, cy - hw),
                              special_flags=pygame.BLEND_RGBA_ADD)

    def _goal_glow_surface(self, color, alpha: int) -> pygame.Surface:
        alpha = max(0, min(255, int(alpha)))
        key = (*color[:3], alpha)
        surf = self._goal_glow_surfaces.get(key)
        if surf is None:
            surf = pygame.Surface((8, GOAL_SIZE), pygame.SRCALPHA)
            surf.fill((*color[:3], alpha))
            self._goal_glow_surfaces[key] = surf
        return surf

    def draw_particles(self):
        self.particles.update()
        self.particles.draw(self.surface)

    def draw_flash(self):
        self.flash.update()
        self.flash.draw(self.surface)

    # ── Field surface (pre-rendered) ──────────────────────────────────────────

    def _build_field(self) -> pygame.Surface:
        surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        surf.fill(self.c_bg)

        tw = TABLE_WIDTH
        th = TABLE_HEIGHT

        # ── Vertical stripes ──────────────────────────────────────────────
        num = (tw // self.STRIPE_W) + 2
        for i in range(num):
            x = TABLE_LEFT + i * self.STRIPE_W
            w = min(self.STRIPE_W, TABLE_RIGHT - x)
            if w <= 0:
                break
            color = self.c_light if i % 2 == 0 else self.c_dark
            pygame.draw.rect(surf, color, (x, TABLE_TOP, w, th))

        # ── White field markings ──────────────────────────────────────────
        lw = 2   # line width

        # Outer border
        pygame.draw.rect(surf, self.c_line,
                         (TABLE_LEFT, TABLE_TOP, tw, th), lw)

        # Center line (Vertical)
        pygame.draw.line(surf, self.c_line,
                         (TABLE_CENTER_X, TABLE_TOP),
                         (TABLE_CENTER_X, TABLE_BOTTOM), lw)

        # Center circle
        pygame.draw.circle(surf, self.c_line,
                           (TABLE_CENTER_X, TABLE_CENTER_Y), 72, lw)
        # Center dot
        pygame.draw.circle(surf, self.c_line,
                           (TABLE_CENTER_X, TABLE_CENTER_Y), 5)

        cy  = TABLE_CENTER_Y
        hw  = GOAL_HALF

        # ── Goal areas (penalty boxes) ────────────────────────────────────
        pbox_w = 65
        pbox_h = GOAL_SIZE + 100
        # Left penalty box
        pygame.draw.rect(surf, self.c_line,
                         (TABLE_LEFT, cy - pbox_h // 2,
                          pbox_w, pbox_h), lw)
        # Right penalty box
        pygame.draw.rect(surf, self.c_line,
                         (TABLE_RIGHT - pbox_w, cy - pbox_h // 2,
                          pbox_w, pbox_h), lw)

        # ── 6-yard boxes ──────────────────────────────────────────────────
        sbox_w = 30
        sbox_h = GOAL_SIZE + 30
        pygame.draw.rect(surf, self.c_line,
                         (TABLE_LEFT, cy - sbox_h // 2,
                          sbox_w, sbox_h), lw)
        pygame.draw.rect(surf, self.c_line,
                         (TABLE_RIGHT - sbox_w, cy - sbox_h // 2,
                          sbox_w, sbox_h), lw)

        # ── Penalty spots ─────────────────────────────────────────────────
        pygame.draw.circle(surf, self.c_line,
                           (TABLE_LEFT + 90, cy), 4)
        pygame.draw.circle(surf, self.c_line,
                           (TABLE_RIGHT - 90, cy), 4)

        # ── Corner arcs ───────────────────────────────────────────────────
        cr = 18   # corner arc radius
        for (bx, by, start, stop) in [
            (TABLE_LEFT,  TABLE_TOP,    -math.pi / 2, 0),
            (TABLE_RIGHT, TABLE_TOP,    math.pi, 3 * math.pi / 2),
            (TABLE_LEFT,  TABLE_BOTTOM, 0, math.pi / 2),
            (TABLE_RIGHT, TABLE_BOTTOM, math.pi / 2, math.pi),
        ]:
            arc_r = pygame.Rect(bx - cr, by - cr, cr * 2, cr * 2)
            try:
                pygame.draw.arc(surf, self.c_line, arc_r, start, stop, lw)
            except Exception:
                pass

        # ── Goal nets ─────────────────────────────────────────────────────
        net_d = 28   # net depth
        self._draw_net(surf, TABLE_LEFT - net_d, cy - hw, net_d, GOAL_SIZE)
        self._draw_net(surf, TABLE_RIGHT,        cy - hw, net_d, GOAL_SIZE)

        # Goal mouth color bar
        pygame.draw.rect(surf, C_GOAL_GLOW_P2,
                         (TABLE_LEFT - 4, cy - hw, 4, GOAL_SIZE))
        pygame.draw.rect(surf, C_GOAL_GLOW_P1,
                         (TABLE_RIGHT, cy - hw, 4, GOAL_SIZE))

        # Goal posts
        post_r = 6
        for gy in [cy - hw, cy + hw]:
            pygame.draw.circle(surf, self.c_line, (TABLE_LEFT, gy),  post_r)
            pygame.draw.circle(surf, self.c_line, (TABLE_RIGHT, gy), post_r)

        return surf

    def _draw_net(self, surf, x, y, w, h):
        """Draw a grid-pattern net rectangle."""
        net = pygame.Surface((w, h), pygame.SRCALPHA)
        net.fill((30, 30, 30, 140))
        # Vertical lines
        for nx in range(0, w, 14):
            pygame.draw.line(net, (200, 200, 200, 60), (nx, 0), (nx, h), 1)
        # Horizontal lines
        for ny in range(0, h, 10):
            pygame.draw.line(net, (200, 200, 200, 60), (0, ny), (w, ny), 1)
        # Border
        pygame.draw.rect(net, (220, 220, 220, 120), (0, 0, w, h), 1)
        surf.blit(net, (x, y))

    def _build_score_bar(self) -> pygame.Surface:
        """Top score bar background."""
        surf = pygame.Surface((WINDOW_WIDTH, SCORE_BAR_HEIGHT))
        surf.fill(C_SCORE_BAR)
        # Bottom separator line
        pygame.draw.line(surf, self.c_line, (0, SCORE_BAR_HEIGHT - 2), (WINDOW_WIDTH, SCORE_BAR_HEIGHT - 2), 2)
        return surf
