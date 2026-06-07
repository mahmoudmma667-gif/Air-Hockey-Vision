"""
Air Hockey Vision - UI Components (soccer style)
Score bar, player labels, tracking indicators, FPS counter.
"""

import math
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

        bg_alpha = int(20 + 70 * t)
        bg = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
        bg.fill((*self.color[:3], bg_alpha))
        surface.blit(bg, r.topleft)

        bw = 1 + int(t)
        bc = tuple(int(c * (0.5 + 0.5 * t)) for c in self.color[:3])
        pygame.draw.rect(surface, bc, r, bw, border_radius=8)

        font  = FontCache.get(self.font_size, bold=True)
        color = tuple(min(255, int(c * (0.7 + 0.3 * t))) for c in self.color[:3])
        render_text(surface, self.text, font, color, r.center)


# ─── Soccer-style Score Display ───────────────────────────────────────────────

class ScoreDisplay:
    """Draws the bottom score bar: PLAYER 1  3 : 2  PLAYER 2."""

    def __init__(self, p1_color=C_GOAL_GLOW_P1, p2_color=C_GOAL_GLOW_P2):
        self.p1_color   = p1_color
        self.p2_color   = p2_color
        self._p1_flash  = 0.0
        self._p2_flash  = 0.0

    def flash_p1(self): self._p1_flash = 1.0
    def flash_p2(self): self._p2_flash = 1.0

    def update(self):
        self._p1_flash = max(0.0, self._p1_flash - 0.03)
        self._p2_flash = max(0.0, self._p2_flash - 0.03)

    def draw(self, surface: pygame.Surface, p1_score: int, p2_score: int,
             time_left: float | None, game_mode: str = MODE_VS_AI):
        bar_y = SCORE_BAR_TOP
        bar_h = SCORE_BAR_HEIGHT
        cx    = WINDOW_WIDTH // 2

        font_score = FontCache.get(40, bold=True)
        font_label = FontCache.get(FONT_TINY, bold=True)
        font_timer = FontCache.get(FONT_SMALL)

        # ── Player 1 (left / bottom player) ──────────────────────────────
        p1_pulse = tuple(min(255, int(c * (1 + self._p1_flash * 0.6)))
                         for c in self.p1_color)
        # Color swatch
        pygame.draw.rect(surface, self.p1_color,
                         (20, bar_y + 8, 12, bar_h - 16), border_radius=3)
        render_text(surface, "PLAYER 1", font_label, self.p1_color,
                    (45, bar_y + bar_h // 2 - 10), center=False)
        # Score number
        p1_surf = font_score.render(str(p1_score), True, p1_pulse)
        surface.blit(p1_surf, (cx - 110, bar_y + bar_h // 2 - p1_surf.get_height() // 2))

        # ── Divider ───────────────────────────────────────────────────────
        div_font = FontCache.get(36, bold=True)
        render_text(surface, ":", div_font, C_UI_DIM,
                    (cx, bar_y + bar_h // 2))

        # ── Player 2 / AI (right / top player) ───────────────────────────
        p2_label = "AI" if game_mode == MODE_VS_AI else "PLAYER 2"
        p2_pulse = tuple(min(255, int(c * (1 + self._p2_flash * 0.6)))
                         for c in self.p2_color)
        p2_surf = font_score.render(str(p2_score), True, p2_pulse)
        surface.blit(p2_surf, (cx + 70, bar_y + bar_h // 2 - p2_surf.get_height() // 2))
        render_text(surface, p2_label, font_label, self.p2_color,
                    (WINDOW_WIDTH - 130, bar_y + bar_h // 2 - 10), center=False)
        pygame.draw.rect(surface, self.p2_color,
                         (WINDOW_WIDTH - 32, bar_y + 8, 12, bar_h - 16),
                         border_radius=3)

        # ── Timer ─────────────────────────────────────────────────────────
        if time_left is not None:
            mins   = int(time_left) // 60
            secs   = int(time_left) % 60
            t_str  = f"{mins:01d}:{secs:02d}"
            t_color = (255, 80, 80) if time_left < 10 else C_UI_DIM
            render_text(surface, t_str, font_timer, t_color,
                        (cx, bar_y + bar_h // 2))


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
