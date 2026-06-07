"""
Air Hockey Vision - Stats Screen
Match statistics and historical records.
"""

import pygame
from src.core.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    C_NEON_CYAN, C_NEON_MAGENTA, C_NEON_YELLOW, C_UI_DIM, C_UI_TEXT,
    C_BACKGROUND, STATE_MAIN_MENU,
    FONT_LARGE, FONT_MEDIUM, FONT_SMALL, FONT_TINY,
)
from src.rendering.ui import Button, FontCache, render_text_glow


class StatsScreen:
    """Displays running session statistics."""

    def __init__(self, sound_manager, stats: dict):
        self.sound = sound_manager
        self.stats = stats   # shared dict updated by game

        cx = WINDOW_WIDTH // 2
        self._back_btn = Button(
            pygame.Rect(cx - 120, WINDOW_HEIGHT - 90, 240, 52),
            "← BACK", C_NEON_CYAN
        )

    def update(self, dt: float, mouse_pos, mouse_down: bool) -> str | None:
        if self._back_btn.update(mouse_pos, mouse_down):
            self.sound.play_menu_select()
            return STATE_MAIN_MENU
        return None

    def draw(self, surface: pygame.Surface):
        surface.fill(C_BACKGROUND)
        cx = WINDOW_WIDTH // 2

        render_text_glow(surface, "STATISTICS",
                         FontCache.get(FONT_LARGE, bold=True),
                         C_NEON_YELLOW, (cx, 100),
                         glow_color=(*C_NEON_YELLOW, 80))

        rows = [
            ("Games Played",      self.stats.get('games_played', 0),       C_NEON_CYAN),
            ("P1 Wins",           self.stats.get('p1_wins', 0),            C_NEON_CYAN),
            ("P2 / AI Wins",      self.stats.get('p2_wins', 0),            C_NEON_MAGENTA),
            ("Total Goals",       self.stats.get('total_goals', 0),         C_NEON_YELLOW),
            ("Longest Rally",     self.stats.get('longest_rally', 0),       C_NEON_CYAN),
            ("Fastest Puck (px/f)",self.stats.get('fastest_puck', 0.0),    C_NEON_MAGENTA),
        ]

        y = 185
        for label, value, color in rows:
            # Label
            lbl = FontCache.get(FONT_SMALL).render(label, True, C_UI_DIM)
            surface.blit(lbl, (cx - 280, y))
            # Value
            val_str = f"{value:.1f}" if isinstance(value, float) else str(value)
            render_text_glow(surface, val_str,
                             FontCache.get(FONT_MEDIUM, bold=True),
                             color, (cx + 200, y + 8))
            # Separator line
            pygame.draw.line(surface, (*C_UI_DIM, 40),
                             (cx - 280, y + 36), (cx + 280, y + 36))
            y += 72

        self._back_btn.draw(surface)
