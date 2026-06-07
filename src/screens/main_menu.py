"""
Air Hockey Vision - Main Menu Screen
Polished, professional animated title and mode selection.
"""

import math
import time
import random
import pygame

from src.core.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    C_BACKGROUND, C_NEON_CYAN, C_NEON_MAGENTA, C_NEON_YELLOW,
    C_NEON_PURPLE, C_UI_TEXT, C_UI_DIM, C_WHITE,
    MODE_VS_AI, MODE_TWO_PLAYER, MODE_TRAINING, MODE_CHALLENGE,
    STATE_GAME, STATE_SETTINGS, STATE_STATS,
    AI_DIFFICULTY_EASY, AI_DIFFICULTY_MEDIUM,
    AI_DIFFICULTY_HARD, AI_DIFFICULTY_ADAPTIVE,
    FONT_HUGE, FONT_LARGE, FONT_MEDIUM, FONT_SMALL, FONT_TINY,
)
from src.rendering.ui import Button, FontCache, render_text, render_text_glow
from src.rendering.effects import ParticleSystem, Particle

# Pre-built background surface (expensive, done once)
_BG_CACHE = None


def _build_bg():
    global _BG_CACHE
    surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    surf.fill(C_BACKGROUND)

    # Subtle radial gradient overlay
    cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
    for r in range(500, 50, -30):
        alpha = max(0, 18 - (500 - r) // 20)
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*C_NEON_CYAN, alpha), (r, r), r)
        surf.blit(s, (cx - r, cy - r), special_flags=pygame.BLEND_RGBA_ADD)

    # Horizontal scan lines
    for y in range(0, WINDOW_HEIGHT, 4):
        pygame.draw.line(surf, (255, 255, 255, 6), (0, y), (WINDOW_WIDTH, y))

    _BG_CACHE = surf


class MainMenu:
    def __init__(self, sound_manager):
        self.sound = sound_manager
        self._t    = 0.0

        self._particles  = ParticleSystem()
        self._spawn_t    = 0
        self._sub        = 'main'   # 'main' | 'mode'

        self._difficulties = ['EASY', 'MEDIUM', 'HARD', 'ADAPTIVE']
        self._diff_index   = 1

        self._build_buttons()

    # ── Build buttons ─────────────────────────────────────────────────────────

    def _build_buttons(self):
        cx   = WINDOW_WIDTH // 2
        bw, bh, gap = 320, 56, 10

        def btn(label, y, color=C_NEON_CYAN):
            return Button(pygame.Rect(cx - bw // 2, y, bw, bh), label, color)

        start_y = WINDOW_HEIGHT // 2 - 80
        self._main_btns = [
            btn("▶  PLAY",         start_y,               C_NEON_CYAN),
            btn("⚙  SETTINGS",     start_y + bh + gap,    C_NEON_PURPLE),
            btn("📊  STATISTICS",  start_y + 2*(bh+gap),  C_NEON_YELLOW),
            btn("✕  QUIT",         start_y + 3*(bh+gap),  C_NEON_MAGENTA),
        ]

        mode_start_y = WINDOW_HEIGHT // 2 - 130
        self._mode_btns = [
            btn("🤖  VS AI",        mode_start_y,               C_NEON_CYAN),
            btn("👥  TWO PLAYERS",  mode_start_y + bh + gap,    C_NEON_MAGENTA),
            btn("🎯  TRAINING",     mode_start_y + 2*(bh+gap),  C_NEON_YELLOW),
            btn("⚡  CHALLENGE",    mode_start_y + 3*(bh+gap),  C_NEON_PURPLE),
            btn("←  BACK",         mode_start_y + 4*(bh+gap),  C_UI_DIM),
        ]

        diff_y = mode_start_y + 5*(bh+gap) + 8
        self._diff_left  = Button(
            pygame.Rect(cx - bw//2,      diff_y, 48, 44), "<", C_NEON_CYAN, FONT_MEDIUM)
        self._diff_right = Button(
            pygame.Rect(cx + bw//2 - 48, diff_y, 48, 44), ">", C_NEON_CYAN, FONT_MEDIUM)
        self._diff_rect  = pygame.Rect(cx - bw//2 + 54, diff_y, bw - 108, 44)

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, dt: float, mouse_pos, mouse_down: bool):
        self._t += dt
        self._spawn_ambient()
        self._particles.update()

        if self._sub == 'main':
            return self._update_main(mouse_pos, mouse_down)
        return self._update_mode(mouse_pos, mouse_down)

    def _update_main(self, mouse_pos, mouse_down):
        for i, btn in enumerate(self._main_btns):
            if btn.update(mouse_pos, mouse_down):
                self.sound.play_menu_select()
                if i == 0: self._sub = 'mode'
                elif i == 1: return (STATE_SETTINGS, {})
                elif i == 2: return (STATE_STATS, {})
                elif i == 3: return ('quit', {})
        return None

    def _update_mode(self, mouse_pos, mouse_down):
        modes = [MODE_VS_AI, MODE_TWO_PLAYER, MODE_TRAINING, MODE_CHALLENGE]
        for i, btn in enumerate(self._mode_btns):
            if btn.update(mouse_pos, mouse_down):
                self.sound.play_menu_select()
                if i < 4:
                    return (STATE_GAME,
                            {'mode': modes[i], 'difficulty': self._diff_index})
                else:
                    self._sub = 'main'
        if self._diff_left.update(mouse_pos, mouse_down):
            self.sound.play_menu_hover()
            self._diff_index = (self._diff_index - 1) % 4
        if self._diff_right.update(mouse_pos, mouse_down):
            self.sound.play_menu_hover()
            self._diff_index = (self._diff_index + 1) % 4
        return None

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface):
        global _BG_CACHE
        if _BG_CACHE is None:
            _build_bg()
        surface.blit(_BG_CACHE, (0, 0))

        self._draw_animated_grid(surface)
        self._particles.draw(surface)
        self._draw_title(surface)

        if self._sub == 'main':
            self._draw_main_panel(surface)
        else:
            self._draw_mode_panel(surface)

        self._draw_footer(surface)

    def _draw_animated_grid(self, surface):
        """Subtle animated vertical + horizontal lines."""
        col = (40, 60, 120, 15)
        spacing = 80
        offset_x = int(self._t * 12) % spacing
        for x in range(-spacing + offset_x, WINDOW_WIDTH + spacing, spacing):
            s = pygame.Surface((1, WINDOW_HEIGHT), pygame.SRCALPHA)
            s.fill(col)
            surface.blit(s, (x, 0))
        offset_y = int(self._t * 8) % spacing
        for y in range(-spacing + offset_y, WINDOW_HEIGHT + spacing, spacing):
            s = pygame.Surface((WINDOW_WIDTH, 1), pygame.SRCALPHA)
            s.fill(col)
            surface.blit(s, (0, y))

    def _draw_title(self, surface):
        cx = WINDOW_WIDTH // 2
        pulse = 0.6 + 0.4 * math.sin(self._t * 2.2)

        # Glow halo behind title
        gs = pygame.Surface((700, 140), pygame.SRCALPHA)
        for r in [120, 80, 50, 30]:
            alpha = int(10 * pulse * (120 - r) // 120)
            pygame.draw.ellipse(gs, (*C_NEON_CYAN, alpha), (350 - r * 2, 70 - r // 2, r * 4, r))
        surface.blit(gs, (cx - 350, 80), special_flags=pygame.BLEND_RGBA_ADD)

        # "AIR HOCKEY" — wavy neon characters
        title = "AIR HOCKEY"
        font  = FontCache.get(FONT_HUGE, bold=True)
        total_w = font.size(title)[0]
        base_x  = cx - total_w // 2
        for i, ch in enumerate(title):
            y_off  = int(math.sin(self._t * 3.0 + i * 0.55) * 7)
            # Glow layer
            glow_col = (*C_NEON_CYAN, int(80 * pulse))
            gsurf = font.render(ch, True, glow_col)
            char_w = font.size(title[:i])[0]
            surface.blit(gsurf, (base_x + char_w + 2, 118 + y_off + 2),
                         special_flags=pygame.BLEND_RGBA_ADD)
            # Main layer
            lbl = font.render(ch, True, C_NEON_CYAN)
            surface.blit(lbl, (base_x + char_w, 118 + y_off))

        # "VISION" sub-title
        render_text(surface, "VISION",
                    FontCache.get(FONT_LARGE, bold=True),
                    C_NEON_MAGENTA, (cx, 218), shadow=True)

        # Divider line
        lw = 2
        dw = 380
        pygame.draw.line(surface, (*C_NEON_MAGENTA, 100), (cx - dw//2, 248), (cx + dw//2, 248), lw)

        # Tagline
        render_text(surface, "HAND-TRACKING AIR HOCKEY  •  REAL-TIME COMPUTER VISION",
                    FontCache.get(FONT_TINY), C_UI_DIM, (cx, 266))

    def _draw_panel_bg(self, surface, rect: pygame.Rect, color):
        """Glassmorphism panel background."""
        bg = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        bg.fill((*color[:3], 12))
        surface.blit(bg, rect.topleft)
        pygame.draw.rect(surface, (*color[:3], 60), rect, 1, border_radius=16)

    def _draw_main_panel(self, surface):
        cx = WINDOW_WIDTH // 2
        bw = 320
        start_y = WINDOW_HEIGHT // 2 - 80
        panel_h = 4 * 56 + 3 * 10 + 32
        panel_rect = pygame.Rect(cx - bw // 2 - 20, start_y - 16, bw + 40, panel_h)
        self._draw_panel_bg(surface, panel_rect, C_NEON_CYAN)
        for btn in self._main_btns:
            btn.draw(surface)

    def _draw_mode_panel(self, surface):
        cx = WINDOW_WIDTH // 2
        bw = 320
        mode_start_y = WINDOW_HEIGHT // 2 - 130
        panel_h = 5 * 56 + 4 * 10 + 44 + 32 + 16
        panel_rect = pygame.Rect(cx - bw // 2 - 20, mode_start_y - 16, bw + 40, panel_h)
        self._draw_panel_bg(surface, panel_rect, C_NEON_MAGENTA)

        render_text(surface, "SELECT MODE",
                    FontCache.get(FONT_SMALL, bold=True),
                    C_NEON_YELLOW, (cx, mode_start_y - 4))
        for btn in self._mode_btns:
            btn.draw(surface)

        # Difficulty selector
        self._diff_left.draw(surface)
        self._diff_right.draw(surface)
        dr = self._diff_rect

        # Background pill
        pill = pygame.Surface((dr.width, dr.height), pygame.SRCALPHA)
        pill.fill((*C_NEON_CYAN, 30))
        surface.blit(pill, dr.topleft)
        pygame.draw.rect(surface, C_NEON_CYAN, dr, 1, border_radius=8)
        render_text(surface, f"AI: {self._difficulties[self._diff_index]}",
                    FontCache.get(FONT_SMALL, bold=True), C_NEON_CYAN, dr.center)

    def _draw_footer(self, surface):
        f = FontCache.get(FONT_TINY)
        t = f.render("Air Hockey Vision  •  Hand Tracking Edition  •  2025",
                     True, C_UI_DIM)
        surface.blit(t, t.get_rect(centerx=WINDOW_WIDTH // 2,
                                    bottom=WINDOW_HEIGHT - 8))

        # Version badge
        v = FontCache.get(FONT_TINY)
        vt = v.render("v2.0", True, (*C_NEON_CYAN, 100))
        surface.blit(vt, (WINDOW_WIDTH - 50, WINDOW_HEIGHT - 22))

    def _spawn_ambient(self):
        self._spawn_t += 1
        if self._spawn_t % 8 == 0:
            colors = [C_NEON_CYAN, C_NEON_MAGENTA, C_NEON_YELLOW, C_NEON_PURPLE]
            self._particles._particles.append(
                Particle(
                    random.randint(0, WINDOW_WIDTH),
                    random.randint(WINDOW_HEIGHT // 2, WINDOW_HEIGHT),
                    (random.random() - 0.5) * 0.6,
                    -random.random() * 0.9,
                    random.choice(colors),
                    random.uniform(1.5, 3.5),
                    random.randint(60, 120),
                    gravity=0.0
                )
            )
