"""
Air Hockey Vision - Settings Screen
Volume, camera, difficulty, and display options.
"""

import pygame
from src.core.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    C_NEON_CYAN, C_NEON_MAGENTA, C_NEON_YELLOW, C_UI_DIM, C_UI_TEXT,
    C_BACKGROUND, STATE_MAIN_MENU,
    FONT_LARGE, FONT_MEDIUM, FONT_SMALL, FONT_TINY,
    THEME_NEON, THEME_SOCCER,
)
from src.rendering.ui import Button, FontCache, render_text_glow


class SettingsScreen:
    def __init__(self, sound_manager, settings_state: dict):
        self.sound = sound_manager
        self.state = settings_state   # mutable shared dict

        cx = WINDOW_WIDTH // 2
        self._back_btn = Button(
            pygame.Rect(cx - 120, WINDOW_HEIGHT - 90, 240, 52),
            "← BACK", C_NEON_CYAN
        )

        self._cam_btn = Button(
            pygame.Rect(cx - 160, 480, 320, 48),
            "", C_NEON_YELLOW
        )
        self._theme_btn = Button(
            pygame.Rect(cx - 160, 540, 320, 48),
            "", C_NEON_MAGENTA
        )

        # Sliders: list of (label, key, min, max, rect)
        self._sliders = [
            ("MASTER VOLUME", "volume",       0.0, 1.0),
            ("HAND SMOOTHING","hand_smooth",  0.2, 0.9),
            ("SENSITIVITY",   "sensitivity",  0.1, 1.0),
        ]
        self._slider_rects = []
        for i, (label, key, lo, hi) in enumerate(self._sliders):
            r = pygame.Rect(cx - 200, 190 + i * 100, 400, 12)
            self._slider_rects.append(r)

        self._dragging: int | None = None

    def update(self, dt: float, mouse_pos, mouse_down: bool,
               mouse_just_down: bool) -> str | None:
        if self._back_btn.update(mouse_pos, mouse_down):
            self.sound.play_menu_select()
            return STATE_MAIN_MENU

        # Slider dragging
        for i, (label, key, lo, hi) in enumerate(self._sliders):
            r = self._slider_rects[i]
            if mouse_just_down and r.inflate(0, 20).collidepoint(mouse_pos):
                self._dragging = i
            if self._dragging == i and mouse_down:
                t = (mouse_pos[0] - r.x) / r.width
                t = max(0.0, min(1.0, t))
                self.state[key] = lo + t * (hi - lo)
                if key == 'volume':
                    self.sound.set_master_volume(self.state[key])
        if not mouse_down:
            self._dragging = None

        cam_key = 'show_camera'
        cam_val = self.state.get(cam_key, True)
        self._cam_btn.text = f"CAMERA PREVIEW: {'ON' if cam_val else 'OFF'}"
        if self._cam_btn.update(mouse_pos, mouse_down):
            self.state[cam_key] = not cam_val
            self.sound.play_menu_select()

        theme_key = 'theme'
        theme_val = self.state.get(theme_key, THEME_NEON)
        self._theme_btn.text = f"THEME: {theme_val.upper()}"
        if self._theme_btn.update(mouse_pos, mouse_down):
            self.state[theme_key] = (
                THEME_SOCCER if theme_val == THEME_NEON else THEME_NEON
            )
            self.sound.play_menu_select()

        return None

    def draw(self, surface: pygame.Surface):
        surface.fill(C_BACKGROUND)
        cx = WINDOW_WIDTH // 2

        render_text_glow(surface, "SETTINGS",
                         FontCache.get(FONT_LARGE, bold=True),
                         C_NEON_CYAN, (cx, 120),
                         glow_color=(*C_NEON_CYAN, 80))

        # Sliders
        for i, (label, key, lo, hi) in enumerate(self._sliders):
            r   = self._slider_rects[i]
            val = self.state.get(key, 0.5)
            t   = (val - lo) / (hi - lo)

            # Label
            render_text_glow(surface, label, FontCache.get(FONT_SMALL),
                             C_UI_TEXT, (cx, r.top - 20))

            # Track
            pygame.draw.rect(surface, (*C_UI_DIM, 80),
                             r, border_radius=6)
            # Fill
            fill_r = pygame.Rect(r.x, r.y, int(r.width * t), r.height)
            pygame.draw.rect(surface, C_NEON_CYAN, fill_r, border_radius=6)
            # Handle
            hx = r.x + int(r.width * t)
            pygame.draw.circle(surface, C_NEON_CYAN, (hx, r.centery), 10)
            pygame.draw.circle(surface, (255, 255, 255, 200), (hx, r.centery), 4)

            # Value text
            val_str = f"{val:.2f}" if isinstance(val, float) else str(val)
            render_text_glow(surface, val_str,
                             FontCache.get(FONT_SMALL), C_UI_DIM,
                             (cx + 230, r.centery), center=False)

        cam_val = self.state.get('show_camera', True)
        self._cam_btn.text = f"CAMERA PREVIEW: {'ON' if cam_val else 'OFF'}"
        self._cam_btn.draw(surface)

        theme_val = self.state.get('theme', THEME_NEON)
        self._theme_btn.text = f"THEME: {theme_val.upper()}"
        self._theme_btn.draw(surface)

        self._back_btn.draw(surface)
