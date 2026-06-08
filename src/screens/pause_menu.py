"""
Air Hockey Vision - Pause Menu Screen
Professional overlay with pygame-drawn icons — no Unicode glyph issues.
"""

import math
import pygame
from src.core.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    C_BACKGROUND, C_NEON_CYAN, C_NEON_MAGENTA, C_NEON_YELLOW, C_UI_DIM,
    STATE_GAME, STATE_MAIN_MENU, STATE_SETTINGS,
    FONT_LARGE, FONT_MEDIUM, FONT_SMALL, FONT_TINY,
)
from src.rendering.ui import FontCache, render_text_glow


# ─── Inline icon painter (mirrors main_menu.draw_icon) ────────────────────────
def _draw_icon(surface: pygame.Surface, icon_type: str,
               cx: int, cy: int, size: int, color: tuple, alpha: int = 220):
    s  = pygame.Surface((size * 2 + 6, size * 2 + 6), pygame.SRCALPHA)
    ic = (size + 3, size + 3)
    c  = (*color[:3], alpha)

    if icon_type == 'resume':
        # Double-triangle (play) symbol
        hs = size // 2
        pygame.draw.polygon(s, c, [
            (ic[0] - hs - 2, ic[1] - hs),
            (ic[0] + 1,      ic[1]),
            (ic[0] - hs - 2, ic[1] + hs),
        ])
        pygame.draw.polygon(s, c, [
            (ic[0] + 1,      ic[1] - hs),
            (ic[0] + hs + 2, ic[1]),
            (ic[0] + 1,      ic[1] + hs),
        ])

    elif icon_type == 'restart':
        # Circular arrow (two arcs + arrowhead)
        r = size // 2
        pygame.draw.arc(s, c,
                        (ic[0]-r, ic[1]-r, r*2, r*2),
                        math.radians(30), math.radians(320), 2)
        # Arrowhead at end of arc
        ax = ic[0] + int(math.cos(math.radians(30)) * r)
        ay = ic[1] - int(math.sin(math.radians(30)) * r)
        pygame.draw.polygon(s, c, [
            (ax, ay - 5), (ax + 5, ay + 3), (ax - 5, ay + 3)
        ])

    elif icon_type == 'settings':
        r = max(3, size // 2)
        pygame.draw.circle(s, c, ic, r, 2)
        pygame.draw.circle(s, c, ic, max(1, r // 3))
        for ang in range(0, 360, 45):
            rad = math.radians(ang)
            x1 = ic[0] + int(math.cos(rad) * (r - 1))
            y1 = ic[1] + int(math.sin(rad) * (r - 1))
            x2 = ic[0] + int(math.cos(rad) * (r + 4))
            y2 = ic[1] + int(math.sin(rad) * (r + 4))
            pygame.draw.line(s, c, (x1, y1), (x2, y2), 2)

    elif icon_type == 'home':
        # House silhouette: roof triangle + door rect
        hs = size // 2
        # Roof
        pygame.draw.polygon(s, c, [
            (ic[0], ic[1] - hs),
            (ic[0] - hs, ic[1]),
            (ic[0] + hs, ic[1]),
        ], 2)
        # Body
        pygame.draw.rect(s, c,
                         (ic[0] - hs + 3, ic[1], hs * 2 - 6, hs - 2), 2)
        # Door
        pygame.draw.rect(s, c,
                         (ic[0] - 4, ic[1] + hs // 2 - 2, 8, hs - 4))

    surface.blit(s, (cx - size - 3, cy - size - 3))


# ─── Pause Button ─────────────────────────────────────────────────────────────
class _PauseBtn:
    """Lightweight button styled consistently with ProButton."""

    def __init__(self, rect: pygame.Rect, label: str,
                 icon_type: str, accent: tuple):
        self.rect      = rect
        self.label     = label
        self.icon_type = icon_type
        self.accent    = accent

        self._hover_x  = 0.0
        self._hover_v  = 0.0
        self.hovered   = False
        self.pressed   = False
        self._was_pressed = False

    def update(self, mouse_pos, mouse_down: bool) -> bool:
        self.hovered = self.rect.collidepoint(mouse_pos)
        was = self._was_pressed
        self._was_pressed = self.hovered and mouse_down

        target = 1.0 if self.hovered else 0.0
        self._hover_v += (target - self._hover_x) * 0.22
        self._hover_v *= 0.72
        self._hover_x  = max(0.0, min(1.0, self._hover_x + self._hover_v))

        return was and not self._was_pressed and self.hovered

    def draw(self, surface: pygame.Surface):
        t = self._hover_x
        r = self.rect

        # Background
        bg_s = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
        bg_s.fill((8, 12, 24, int(10 + 22 * t)))
        if t > 0.08:
            tint = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
            tint.fill((*self.accent[:3], int(12 * t)))
            bg_s.blit(tint, (0, 0))
        surface.blit(bg_s, r.topleft)

        # Border
        brd = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
        pygame.draw.rect(brd, (*self.accent[:3], int(35 + 120 * t)),
                         brd.get_rect(), 1, border_radius=10)
        surface.blit(brd, r.topleft)

        # Left accent bar (on hover)
        if t > 0.05:
            bar_h = r.height - 14
            bar_s = pygame.Surface((2, bar_h), pygame.SRCALPHA)
            for yi in range(bar_h):
                fa = int(180 * t * math.sin(math.pi * yi / bar_h))
                bar_s.set_at((0, yi), (*self.accent[:3], fa))
                bar_s.set_at((1, yi), (*self.accent[:3], fa // 3))
            surface.blit(bar_s, (r.left + 5, r.top + 7))

        # Icon + label
        font   = FontCache.get(FONT_MEDIUM, bold=True)
        col    = (255, 255, 255) if t > 0.4 else (160, 175, 210)
        lab_s  = font.render(self.label, True, col)
        icon_size = 13
        total_w   = icon_size * 2 + 8 + lab_s.get_width()
        ix = r.centerx - total_w // 2 + icon_size
        lx = ix + icon_size + 8
        ly = r.centery - lab_s.get_height() // 2

        ia = int(160 + 60 * t)
        _draw_icon(surface, self.icon_type, ix, r.centery, icon_size,
                   self.accent, ia)
        surface.blit(lab_s, (lx, ly))


# ─── PauseMenu ────────────────────────────────────────────────────────────────
class PauseMenu:
    def __init__(self, sound_manager):
        self.sound = sound_manager
        cx = WINDOW_WIDTH  // 2
        bw, bh, gap = 300, 54, 10
        start_y = 255

        specs = [
            ("RESUME",    'resume',   C_NEON_CYAN),
            ("RESTART",   'restart',  C_NEON_YELLOW),
            ("SETTINGS",  'settings', C_NEON_MAGENTA),
            ("MAIN MENU", 'home',     (100, 110, 150)),
        ]
        self._buttons = [
            _PauseBtn(
                pygame.Rect(cx - bw // 2, start_y + i * (bh + gap), bw, bh),
                label, icon, color
            )
            for i, (label, icon, color) in enumerate(specs)
        ]

        # Semi-transparent backdrop
        self._overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT),
                                       pygame.SRCALPHA)
        self._overlay.fill((0, 0, 8, 172))

        # Panel rect behind buttons
        total_h = len(specs) * bh + (len(specs) - 1) * gap
        self._panel = pygame.Rect(
            cx - bw // 2 - 24, start_y - 20,
            bw + 48, total_h + 40
        )

    def update(self, dt: float, mouse_pos, mouse_down: bool) -> str | None:
        for i, btn in enumerate(self._buttons):
            if btn.update(mouse_pos, mouse_down):
                self.sound.play_menu_select()
                return ['resume', 'restart', STATE_SETTINGS, STATE_MAIN_MENU][i]
        return None

    def draw(self, surface: pygame.Surface):
        surface.blit(self._overlay, (0, 0))

        # Glass panel
        ps = pygame.Surface((self._panel.width, self._panel.height),
                             pygame.SRCALPHA)
        ps.fill((8, 12, 28, 14))
        pygame.draw.rect(ps, (*C_NEON_CYAN, 28),
                         ps.get_rect(), 1, border_radius=16)
        surface.blit(ps, self._panel.topleft)

        # Title
        cx = WINDOW_WIDTH // 2
        render_text_glow(surface, "PAUSED",
                         FontCache.get(FONT_LARGE, bold=True),
                         C_NEON_CYAN, (cx, 205),
                         glow_color=(*C_NEON_CYAN, 70))

        for btn in self._buttons:
            btn.draw(surface)
