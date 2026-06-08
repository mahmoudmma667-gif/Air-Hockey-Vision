"""
Air Hockey Vision - UI Components (soccer style)
Score bar, player labels, tracking indicators, FPS counter.
"""

import math
import random
import pygame
from src.core.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    SCORE_BAR_TOP, SCORE_BAR_HEIGHT,
    TABLE_CENTER_X, TABLE_CENTER_Y,
    C_PADDLE_P1, C_PADDLE_P2, C_PADDLE_AI,
    C_SCORE_BAR, C_WHITE, C_UI_DIM, C_UI_TEXT,
    C_FIELD_LINE, C_NEON_YELLOW, C_NEON_CYAN,
    C_GOAL_GLOW_P1, C_GOAL_GLOW_P2,
    FONT_HUGE, FONT_LARGE, FONT_MEDIUM, FONT_SMALL, FONT_TINY,
    MODE_VS_AI,
)


class FontCache:
    _cache: dict = {}

    @classmethod
    def get(cls, size: int, bold: bool = False) -> pygame.font.Font:
        key = (size, bold)
        if key not in cls._cache:
            try:
                cls._cache[key] = pygame.font.SysFont("Segoe UI", size, bold=bold)
            except Exception:
                cls._cache[key] = pygame.font.Font(None, size)
        return cls._cache[key]


def render_text(surface, text, font, color, pos, center=True,
                shadow=False, shadow_color=(0,0,0)):
    if shadow:
        s = font.render(text, True, shadow_color)
        r = s.get_rect()
        if center: r.center = (pos[0]+2, pos[1]+2)
        else:      r.topleft = (pos[0]+2, pos[1]+2)
        surface.blit(s, r)
    surf = font.render(text, True, color)
    r    = surf.get_rect()
    if center: r.center = pos
    else:      r.topleft = pos
    surface.blit(surf, r)


def render_text_glow(surface, text, font, color, pos,
                     glow_color=None, center=True):
    """Kept for compatibility with main_menu / overlays."""
    render_text(surface, text, font, color, pos, center=center,
                shadow=True, shadow_color=(0,0,0))


# ─── Animated Button ──────────────────────────────────────────────────────────

class Button:
    def __init__(self, rect: pygame.Rect, text: str,
                 color=C_NEON_CYAN, font_size: int = FONT_MEDIUM):
        self.rect      = rect
        self.text      = text
        self.color     = color
        self.font_size = font_size
        self.hovered   = False
        self.pressed   = False
        self._hover_t  = 0.0

    def update(self, mouse_pos, mouse_down: bool) -> bool:
        was_pressed  = self.pressed
        self.hovered = self.rect.collidepoint(mouse_pos)
        self.pressed = self.hovered and mouse_down
        self._hover_t += ((1.0 if self.hovered else 0.0) - self._hover_t) * 0.18
        return was_pressed and not self.pressed and self.hovered

    def draw(self, surface: pygame.Surface):
        t = self._hover_t
        r = self.rect

        bg_alpha = int(10 + 30 * t)
        bg = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
        bg.fill((255, 255, 255, bg_alpha))
        surface.blit(bg, r.topleft)

        bw = 1 if t < 0.1 else 2
        bc_alpha = int(80 + 175 * t)
        bc = (*self.color[:3], bc_alpha)
        
        border_surf = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
        pygame.draw.rect(border_surf, bc, border_surf.get_rect(), bw, border_radius=12)
        surface.blit(border_surf, r.topleft)

        font  = FontCache.get(self.font_size, bold=True)
        if t > 0.1:
            render_text_glow(surface, self.text, font, C_WHITE, r.center, glow_color=self.color)
        else:
            color = tuple(min(255, int(c * 0.8 + 255 * 0.2)) for c in self.color[:3])
            render_text(surface, self.text, font, color, r.center)


# ─── Soccer-style Score Display ───────────────────────────────────────────────

class ScoreDisplay:
    """Draws the bottom score bar: PLAYER 1  3 : 2  PLAYER 2."""

    def __init__(self, p1_color=C_GOAL_GLOW_P1, p2_color=C_GOAL_GLOW_P2):
        self.p1_color   = p1_color
        self.p2_color   = p2_color
        self._p1_flash  = 0.0
        self._p2_flash  = 0.0
        self._p1_shake  = (0, 0)
        self._p2_shake  = (0, 0)

    def flash_p1(self): self._p1_flash = 1.0
    def flash_p2(self): self._p2_flash = 1.0

    def update(self):
        self._p1_flash = max(0.0, self._p1_flash - 0.025)
        self._p2_flash = max(0.0, self._p2_flash - 0.025)
        # Score-number shake: jitter while flash is hot
        if self._p1_flash > 0.2:
            amp = max(1, int(4 * self._p1_flash))
            self._p1_shake = (random.randint(-amp, amp), random.randint(-amp, amp))
        else:
            self._p1_shake = (0, 0)
        if self._p2_flash > 0.2:
            amp = max(1, int(4 * self._p2_flash))
            self._p2_shake = (random.randint(-amp, amp), random.randint(-amp, amp))
        else:
            self._p2_shake = (0, 0)

    def _draw_user_icon(self, surface: pygame.Surface, x: int, y: int, color: tuple):
        # Head
        pygame.draw.circle(surface, color, (x + 10, y + 6), 4)
        # Shoulders (body arc)
        pygame.draw.arc(surface, color, (x + 3, y + 10, 14, 10), 0, math.pi, 2)
        # Shoulder bottom line
        pygame.draw.line(surface, color, (x + 3, y + 15), (x + 17, y + 15), 2)

    def _draw_cpu_icon(self, surface: pygame.Surface, x: int, y: int, color: tuple):
        # Central body
        pygame.draw.rect(surface, color, (x + 4, y + 4, 12, 12), 2, border_radius=2)
        # Inner core
        pygame.draw.rect(surface, color, (x + 7, y + 7, 6, 6))
        # Top pins
        pygame.draw.line(surface, color, (x + 6, y + 1), (x + 6, y + 3), 1)
        pygame.draw.line(surface, color, (x + 10, y + 1), (x + 10, y + 3), 1)
        pygame.draw.line(surface, color, (x + 14, y + 1), (x + 14, y + 3), 1)
        # Bottom pins
        pygame.draw.line(surface, color, (x + 6, y + 17), (x + 6, y + 19), 1)
        pygame.draw.line(surface, color, (x + 10, y + 17), (x + 10, y + 19), 1)
        pygame.draw.line(surface, color, (x + 14, y + 17), (x + 14, y + 19), 1)
        # Left pins
        pygame.draw.line(surface, color, (x + 1, y + 6), (x + 3, y + 6), 1)
        pygame.draw.line(surface, color, (x + 1, y + 10), (x + 3, y + 10), 1)
        pygame.draw.line(surface, color, (x + 1, y + 14), (x + 3, y + 14), 1)
        # Right pins
        pygame.draw.line(surface, color, (x + 17, y + 6), (x + 19, y + 6), 1)
        pygame.draw.line(surface, color, (x + 17, y + 10), (x + 19, y + 10), 1)
        pygame.draw.line(surface, color, (x + 17, y + 14), (x + 19, y + 14), 1)

    def draw(self, surface: pygame.Surface, p1_score: int, p2_score: int,
             time_left: float | None, game_mode: str = MODE_VS_AI):
        bar_y = SCORE_BAR_TOP
        bar_h = SCORE_BAR_HEIGHT
        cx    = WINDOW_WIDTH // 2

        font_score = FontCache.get(44, bold=True)
        font_label = FontCache.get(FONT_SMALL, bold=True)
        font_timer = FontCache.get(FONT_SMALL)

        # Score number centers (with shake offsets applied)
        p1_cx = cx - 100 + self._p1_shake[0]
        p1_cy = bar_y + bar_h // 2 + self._p1_shake[1]
        p2_cx = cx + 100 + self._p2_shake[0]
        p2_cy = bar_y + bar_h // 2 + self._p2_shake[1]

        # ── LAYER 1: Radial score-glow (BEHIND number, normal alpha) ──────────
        # This creates a colour halo centred exactly on the score digit.
        # It uses normal SRCALPHA blending so it never washes out colours drawn on top.
        def _draw_radial_glow(cx_: int, cy_: int, color, flash: float):
            if flash <= 0:
                return
            r_max = int(bar_h * 0.9)
            glow = pygame.Surface((r_max * 2, r_max * 2), pygame.SRCALPHA)
            for step in range(8, 0, -1):
                r = r_max * step // 8
                a = int(flash * 110 * step / 8)
                pygame.draw.circle(glow, (*color[:3], min(255, a)), (r_max, r_max), r)
            surface.blit(glow, (cx_ - r_max, cy_ - r_max))

        _draw_radial_glow(p1_cx, p1_cy, self.p1_color, self._p1_flash)
        _draw_radial_glow(p2_cx, p2_cy, self.p2_color, self._p2_flash)

        # ── LAYER 2: Animated accent underlines ───────────────────────────────
        p1_pulse = tuple(min(255, int(c * (1 + self._p1_flash * 1.0))) for c in self.p1_color)
        p2_pulse = tuple(min(255, int(c * (1 + self._p2_flash * 1.0))) for c in self.p2_color)

        line_y = bar_y + bar_h - 9          # 9 px from bar bottom — never touches separator
        lw1 = max(2, int(2 + self._p1_flash * 4))
        lw2 = max(2, int(2 + self._p2_flash * 4))
        pygame.draw.line(surface, p1_pulse, (20, line_y), (cx - 40, line_y), lw1)
        pygame.draw.line(surface, p2_pulse, (cx + 40, line_y), (WINDOW_WIDTH - 20, line_y), lw2)

        # ── LAYER 3: Player labels + icons ────────────────────────────────────
        text_w_p1, _ = font_label.size("PLAYER 1")
        total_w_p1 = 20 + 8 + text_w_p1
        start_x_p1 = 110 - total_w_p1 // 2
        start_y_p1 = bar_y + (bar_h - 20) // 2
        self._draw_user_icon(surface, start_x_p1, start_y_p1, p1_pulse)
        render_text_glow(surface, "PLAYER 1", font_label, p1_pulse,
                         (start_x_p1 + 28 + text_w_p1 // 2, bar_y + bar_h // 2),
                         glow_color=(*p1_pulse[:3], 100))

        p2_label = "AI" if game_mode == MODE_VS_AI else "PLAYER 2"
        text_w_p2, _ = font_label.size(p2_label)
        total_w_p2 = 20 + 8 + text_w_p2
        rx = WINDOW_WIDTH - 220
        start_x_p2 = rx + 110 - total_w_p2 // 2
        start_y_p2 = bar_y + (bar_h - 20) // 2
        if game_mode == MODE_VS_AI:
            self._draw_cpu_icon(surface, start_x_p2, start_y_p2, p2_pulse)
        else:
            self._draw_user_icon(surface, start_x_p2, start_y_p2, p2_pulse)
        render_text_glow(surface, p2_label, font_label, p2_pulse,
                         (start_x_p2 + 28 + text_w_p2 // 2, bar_y + bar_h // 2),
                         glow_color=(*p2_pulse[:3], 100))

        # ── LAYER 4: Dark badge behind score digit (contrast protection) ───────
        # This ensures the digit is always readable even at full glow intensity.
        for (scx, scy, flash_v) in [(p1_cx, p1_cy, self._p1_flash),
                                     (p2_cx, p2_cy, self._p2_flash)]:
            badge_a = min(210, int(80 + flash_v * 130))
            badge = pygame.Surface((64, 56), pygame.SRCALPHA)
            badge.fill((0, 0, 0, badge_a))
            surface.blit(badge, badge.get_rect(center=(scx, scy)))

        # ── LAYER 5: Score digits (always on top, high contrast) ──────────────
        # Colour transitions: player-hue → bright white at peak flash
        def _score_color(base_color, flash: float) -> tuple:
            if flash > 0.45:
                t = (flash - 0.45) / 0.55
                return tuple(min(255, int(base_color[i] + (255 - base_color[i]) * t))
                             for i in range(3))
            return tuple(min(255, int(c * (1 + flash * 0.6))) for c in base_color)

        def _draw_score(surf, val, color, scx, scy, flash):
            s = font_score.render(str(val), True, color)
            if flash > 0:
                sc = 1.0 + flash * 0.28
                s  = pygame.transform.smoothscale(
                    s, (int(s.get_width() * sc), int(s.get_height() * sc)))
            surf.blit(s, s.get_rect(center=(scx, scy)))

        _draw_score(surface, p1_score,
                    _score_color(self.p1_color, self._p1_flash),
                    p1_cx, p1_cy, self._p1_flash)

        # Divider
        render_text(surface, ":", FontCache.get(36, bold=True), C_UI_DIM,
                    (cx, bar_y + bar_h // 2 - 2))

        _draw_score(surface, p2_score,
                    _score_color(self.p2_color, self._p2_flash),
                    p2_cx, p2_cy, self._p2_flash)

        # ── Timer ─────────────────────────────────────────────────────────────
        if time_left is not None:
            mins   = int(time_left) // 60
            secs   = int(time_left) % 60
            t_str  = f"{mins:01d}:{secs:02d}"
            t_color = (255, 80, 80) if time_left < 10 else C_UI_DIM
            render_text(surface, t_str, font_timer, t_color,
                        (cx, bar_y + bar_h // 2 + 25))


# ─── Tracking Indicator ───────────────────────────────────────────────────────

def draw_tracking_indicator(surface, quality: float, is_tracking: bool,
                             pos, label: str = ""):
    color = (0, 220, 80) if is_tracking else (160, 60, 60)
    pygame.draw.circle(surface, color, pos, 6)
    if label:
        f = FontCache.get(FONT_TINY)
        t = f.render(label, True, color)
        surface.blit(t, (pos[0] + 10, pos[1] - 7))


# ─── FPS Counter ─────────────────────────────────────────────────────────────

def draw_fps(surface, fps: float, pos=(6, 6)):
    color = (0, 220, 80) if fps >= 55 else (255, 200, 0) if fps >= 30 else (255, 60, 60)
    f = FontCache.get(FONT_TINY)
    surface.blit(f.render(f"FPS {fps:.0f}", True, color), pos)
