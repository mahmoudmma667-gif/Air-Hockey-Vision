"""
Air Hockey Vision - Pause Menu Screen
Transparent overlay with neon buttons.
"""

import pygame
from src.core.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    C_BACKGROUND, C_NEON_CYAN, C_NEON_MAGENTA, C_NEON_YELLOW, C_UI_DIM,
    STATE_GAME, STATE_MAIN_MENU, STATE_SETTINGS,
    FONT_LARGE, FONT_MEDIUM,
)
from src.rendering.ui import Button, FontCache, render_text_glow


class PauseMenu:
    def __init__(self, sound_manager):
        self.sound = sound_manager
        cx = WINDOW_WIDTH // 2
        bw, bh, gap = 280, 52, 12

        def btn(label, y, color=C_NEON_CYAN):
            return Button(pygame.Rect(cx - bw // 2, y, bw, bh), label, color)

        self._buttons = [
            btn("▶  RESUME",          280, C_NEON_CYAN),
            btn("🔄  RESTART",         280 + bh + gap,       C_NEON_YELLOW),
            btn("⚙  SETTINGS",        280 + 2 * (bh + gap), C_NEON_MAGENTA),
            btn("🏠  MAIN MENU",       280 + 3 * (bh + gap), C_UI_DIM),
        ]

        self._overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        self._overlay.fill((0, 0, 0, 160))

    def update(self, dt: float, mouse_pos, mouse_down: bool) -> str | None:
        """
        Returns:
          'resume'     – unpause
          'restart'    – restart match
          STATE_SETTINGS
          STATE_MAIN_MENU
          None         – stay on pause
        """
        for i, btn in enumerate(self._buttons):
            if btn.update(mouse_pos, mouse_down):
                self.sound.play_menu_select()
                return ['resume', 'restart', STATE_SETTINGS, STATE_MAIN_MENU][i]
        return None

    def draw(self, surface: pygame.Surface):
        surface.blit(self._overlay, (0, 0))

        cx = WINDOW_WIDTH // 2
        render_text_glow(surface, "PAUSED",
                         FontCache.get(FONT_LARGE, bold=True),
                         C_NEON_CYAN, (cx, 210),
                         glow_color=(*C_NEON_CYAN, 80))

        for btn in self._buttons:
            btn.draw(surface)
