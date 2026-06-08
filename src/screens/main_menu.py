"""
Air Hockey Vision — Main Menu Screen
World-class professional UI redesign:
  • Harmonious dark color palette (deep navy + electric accents)
  • Procedural logo with puck icon + gradient text
  • Glassmorphism panels with real depth
  • Smooth spring-eased button animations
  • Animated grid background + aurora orbs + drifting particles
  • No text overlap — strict layout grid
"""

import math
import time
import random
import pygame

from src.core.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    C_NEON_CYAN, C_NEON_MAGENTA, C_NEON_YELLOW,
    C_NEON_PURPLE, C_UI_TEXT, C_UI_DIM, C_WHITE,
    MODE_VS_AI, MODE_TWO_PLAYER, MODE_TRAINING, MODE_CHALLENGE,
    STATE_GAME, STATE_SETTINGS, STATE_STATS,
    AI_DIFFICULTY_EASY, AI_DIFFICULTY_MEDIUM,
    AI_DIFFICULTY_HARD, AI_DIFFICULTY_ADAPTIVE,
    FONT_HUGE, FONT_LARGE, FONT_MEDIUM, FONT_SMALL, FONT_TINY,
)
from src.rendering.ui import Button, FontCache, render_text, render_text_glow
from src.rendering.effects import ParticleSystem, Particle

# ─── Professional Color Palette ───────────────────────────────────────────────
# Deep navy base with carefully tuned electric accents
COL_BG          = (6,   8,  18)      # Near-black deep navy
COL_SURFACE     = (12,  15,  28)     # Panel base
COL_BORDER      = (30,  40,  80)     # Subtle border
COL_ACCENT_A    = (0,  200, 255)     # Electric cyan (primary)
COL_ACCENT_B    = (200,  40, 255)    # Vivid violet (secondary)
COL_ACCENT_C    = (255, 180,   0)    # Warm gold (highlight)
COL_ACCENT_D    = (40,  255, 140)    # Mint green (success)
COL_TEXT_PRI    = (235, 240, 255)    # Bright white-blue text
COL_TEXT_SEC    = (140, 155, 195)    # Muted secondary text
COL_TEXT_DIM    = (70,  82, 120)     # Very dim hint text

# Mode button color map (icon color per mode)
MODE_COLORS = [COL_ACCENT_A, COL_ACCENT_B, COL_ACCENT_C, COL_ACCENT_D]


# ─── Easing helpers ───────────────────────────────────────────────────────────
def ease_out_cubic(t: float) -> float:
    return 1 - (1 - t) ** 3

def ease_in_out_sine(t: float) -> float:
    return -(math.cos(math.pi * t) - 1) / 2

def lerp(a, b, t):
    return a + (b - a) * t


# ─── Animated Background ─────────────────────────────────────────────────────
class ProBackground:
    """Professional layered background: grid + aurora orbs + scanlines."""

    def __init__(self):
        self._t = 0.0
        self._orbs = []
        # Muted, dark accent colors — NOT full-saturation neon
        _orb_colors = [
            (0,  80, 120),   # dark teal
            (80,  20, 140),  # dark violet
            (100, 60,   0),  # dark amber
        ]
        for i in range(3):
            r = random.randint(60, 130)
            color = _orb_colors[i]
            surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            for dist in range(r, 0, -12):
                a = int(4 * (1 - dist / r))   # max alpha 4 — very subtle
                pygame.draw.circle(surf, (*color, a), (r, r), dist)
            self._orbs.append({
                'surf': surf, 'r': r, 'color': color,
                'x': random.uniform(0, WINDOW_WIDTH),
                'y': random.uniform(0, WINDOW_HEIGHT),
                'vx': random.uniform(-3, 3),
                'vy': random.uniform(-3, 3),
                'phase': random.uniform(0, math.tau),
            })

        # Pre-bake static grid surface
        self._grid_surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        self._bake_grid()

    def _bake_grid(self):
        gs = 70
        col = (18, 24, 48, 18)   # very dim blue-grid
        for x in range(0, WINDOW_WIDTH, gs):
            pygame.draw.line(self._grid_surf, col, (x, 0), (x, WINDOW_HEIGHT), 1)
        for y in range(0, WINDOW_HEIGHT, gs):
            pygame.draw.line(self._grid_surf, col, (0, y), (WINDOW_WIDTH, y), 1)

    def update(self, dt: float):
        self._t += dt
        for orb in self._orbs:
            orb['x'] += orb['vx'] * dt
            orb['y'] += orb['vy'] * dt
            if orb['x'] < -orb['r']:  orb['x'] = WINDOW_WIDTH  + orb['r']
            elif orb['x'] > WINDOW_WIDTH  + orb['r']: orb['x'] = -orb['r']
            if orb['y'] < -orb['r']:  orb['y'] = WINDOW_HEIGHT + orb['r']
            elif orb['y'] > WINDOW_HEIGHT + orb['r']: orb['y'] = -orb['r']

    def draw(self, surface: pygame.Surface):
        surface.fill(COL_BG)

        # Aurora orbs
        for orb in self._orbs:
            pulse = 0.85 + 0.15 * math.sin(self._t * 0.7 + orb['phase'])
            s = orb['surf']
            w, h = s.get_size()
            blit_x = int(orb['x'] - orb['r'])
            blit_y = int(orb['y'] - orb['r'])
            surface.blit(s, (blit_x, blit_y), special_flags=pygame.BLEND_RGBA_ADD)

        # Grid overlay
        surface.blit(self._grid_surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)


# ─── Logo Renderer ────────────────────────────────────────────────────────────
class LogoRenderer:
    """
    Draws the 'AIR HOCKEY' title with professional layered text:
      - Multi-layer glow halo
      - Two-tone gradient effect (simulated with two offset renders)
      - 'VISION' subtitle with violet accent
      - Inline puck icon to the left of title
      - Animated shimmer scanline
    """

    def __init__(self):
        self._t = 0.0
        self._shimmer_x = 0.0

    def update(self, dt: float):
        self._t += dt
        self._shimmer_x = (self._shimmer_x + dt * 180) % (WINDOW_WIDTH + 200)

    def draw(self, surface: pygame.Surface):
        cx = WINDOW_WIDTH // 2
        title_y  = 88   # Centerline of "AIR HOCKEY"
        sub_y    = 152  # Centerline of "VISION"
        tag_y    = 192  # Centerline of tagline

        pulse = 0.92 + 0.08 * math.sin(self._t * 1.8)

        # ── Glow backdrop behind title ─────────────────────────────────────
        gw, gh = 700, 110
        glow_s = pygame.Surface((gw, gh), pygame.SRCALPHA)
        for r in range(55, 0, -4):
            a = max(0, int(14 * (1 - r / 55) * pulse))
            pygame.draw.ellipse(glow_s, (*COL_ACCENT_A[:3], a),
                                (gw // 2 - r * 5, gh // 2 - r, r * 10, r * 2))
        surface.blit(glow_s, (cx - gw // 2, title_y - gh // 2),
                     special_flags=pygame.BLEND_RGBA_ADD)

        # ── Draw puck icon (left of title) ────────────────────────────────
        icon_cx = cx - 310
        icon_cy = title_y + 4
        icon_r  = 22
        icon_s  = pygame.Surface((icon_r * 2 + 20, icon_r * 2 + 20), pygame.SRCALPHA)
        ic = (icon_r + 10, icon_r + 10)
        for gr in range(icon_r + 8, 0, -3):
            ga = max(0, int(18 * (1 - gr / (icon_r + 8)) * pulse))
            pygame.draw.circle(icon_s, (*COL_ACCENT_A, ga), ic, gr)
        pygame.draw.circle(icon_s, (20, 25, 50), ic, icon_r)
        pygame.draw.circle(icon_s, COL_ACCENT_A, ic, icon_r, 3)
        # Inner ring lines
        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            x1 = ic[0] + int(math.cos(rad) * 6)
            y1 = ic[1] + int(math.sin(rad) * 6)
            x2 = ic[0] + int(math.cos(rad) * icon_r - 2)
            y2 = ic[1] + int(math.sin(rad) * icon_r - 2)
            pygame.draw.line(icon_s, (*COL_ACCENT_A, 100), (x1, y1), (x2, y2), 1)
        pygame.draw.circle(icon_s, (*COL_ACCENT_A, 160), ic, 5)
        surface.blit(icon_s, (icon_cx - icon_r - 10, icon_cy - icon_r - 10),
                     special_flags=pygame.BLEND_RGBA_ADD)

        # ── Main title: "AIR HOCKEY" ───────────────────────────────────────
        font_title = FontCache.get(FONT_HUGE, bold=True)

        # Deep shadow
        shadow_s = font_title.render("AIR HOCKEY", True, (0, 0, 0))
        sr = shadow_s.get_rect(center=(cx + 4, title_y + 5))
        surface.blit(shadow_s, sr)

        # Soft glow under title — use SRCALPHA surface with colorkey to avoid solid box
        _glow_surf = font_title.render("AIR HOCKEY", True, COL_ACCENT_A[:3])
        _glow_surf.set_colorkey((0, 0, 0))   # make black bg transparent
        _glow_surf.set_alpha(28)              # very subtle glow
        for off in [(4, 0), (-4, 0), (0, 4), (0, -4)]:
            gr2 = _glow_surf.get_rect(center=(cx + off[0], title_y + off[1]))
            surface.blit(_glow_surf, gr2)

        # Main white text
        title_surf = font_title.render("AIR HOCKEY", True, COL_TEXT_PRI)
        title_rect = title_surf.get_rect(center=(cx, title_y))
        surface.blit(title_surf, title_rect)

        # ── "VISION" subtitle ─────────────────────────────────────────────
        font_sub = FontCache.get(FONT_LARGE, bold=True)
        # Soft glow — same colorkey trick
        _vis_glow = font_sub.render("VISION", True, COL_ACCENT_B[:3])
        _vis_glow.set_colorkey((0, 0, 0))
        _vis_glow.set_alpha(30)
        for off in [(3, 0), (-3, 0), (0, 3)]:
            vr = _vis_glow.get_rect(center=(cx + off[0], sub_y + off[1]))
            surface.blit(_vis_glow, vr)
        vis_surf = font_sub.render("VISION", True, COL_ACCENT_B)
        vis_rect = vis_surf.get_rect(center=(cx, sub_y))
        surface.blit(vis_surf, vis_rect)

        # ── Separator line ─────────────────────────────────────────────────
        line_w = 440
        lx0, lx1 = cx - line_w // 2, cx + line_w // 2
        ly = tag_y - 10
        # Gradient line (multi-segment)
        seg = line_w // 3
        pygame.draw.line(surface, (*COL_ACCENT_B, 40), (lx0, ly), (lx0 + seg, ly), 1)
        pygame.draw.line(surface, (*COL_ACCENT_B, 120), (lx0 + seg, ly), (lx1 - seg, ly), 2)
        pygame.draw.line(surface, (*COL_ACCENT_B, 40), (lx1 - seg, ly), (lx1, ly), 1)
        # Center gem
        pygame.draw.circle(surface, COL_ACCENT_B, (cx, ly), 3)

        # ── Tagline ─────────────────────────────────────────────────────
        font_tag = FontCache.get(FONT_TINY, bold=True)
        tag_txt  = "HAND-TRACKING   ·   COMPUTER VISION   ·   REAL-TIME AI"
        # Render each segment with its accent color for a polychrome look
        segs = [("HAND-TRACKING", COL_ACCENT_A),
                ("   ·   ",       COL_TEXT_SEC),
                ("COMPUTER VISION", COL_ACCENT_B),
                ("   ·   ",        COL_TEXT_SEC),
                ("REAL-TIME AI",    COL_ACCENT_D)]
        total_w = sum(font_tag.render(t, True, (0,0,0)).get_width() for t, _ in segs)
        tx = cx - total_w // 2
        ty = tag_y + 4
        for seg_txt, seg_col in segs:
            seg_s = font_tag.render(seg_txt, True, seg_col[:3])
            seg_s.set_alpha(210)
            surface.blit(seg_s, (tx, ty - seg_s.get_height() // 2))
            tx += seg_s.get_width()


# ─── Icon Painter ────────────────────────────────────────────────────────────
def draw_icon(surface: pygame.Surface, icon_type: str,
              cx: int, cy: int, size: int, color: tuple, alpha: int = 220):
    """
    Draw a crisp geometric icon using pygame primitives.
    No Unicode glyphs — works with any font.
    """
    s = pygame.Surface((size * 2 + 6, size * 2 + 6), pygame.SRCALPHA)
    ic = (size + 3, size + 3)   # centre of mini-surface
    c  = (*color[:3], alpha)

    if icon_type == 'play':
        # Solid right-pointing triangle
        hs = size // 2
        pts = [(ic[0] - hs, ic[1] - hs),
               (ic[0] + hs, ic[1]),
               (ic[0] - hs, ic[1] + hs)]
        pygame.draw.polygon(s, c, pts)

    elif icon_type == 'settings':
        # Circle + 8 radiating ticks (gear look)
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

    elif icon_type == 'stats':
        # 3 vertical bars at different heights
        bw = max(2, size // 4)
        for i, frac in enumerate([0.5, 1.0, 0.72]):
            bh = int(frac * size * 0.85)
            bx = ic[0] - size // 2 + i * (bw + 3)
            pygame.draw.rect(s, c, (bx, ic[1] - bh // 2, bw, bh),
                             border_radius=1)

    elif icon_type == 'quit':
        # X cross
        hs = size // 2 - 1
        pygame.draw.line(s, c, (ic[0]-hs, ic[1]-hs), (ic[0]+hs, ic[1]+hs), 3)
        pygame.draw.line(s, c, (ic[0]+hs, ic[1]-hs), (ic[0]-hs, ic[1]+hs), 3)

    elif icon_type == 'robot':
        # Robot head: rect + two dot eyes + antenna
        hw, hh = size // 2, size // 3
        pygame.draw.rect(s, c, (ic[0]-hw, ic[1]-hh, hw*2, hh*2), 2, border_radius=3)
        for ex in [ic[0] - hw//3, ic[0] + hw//3]:
            pygame.draw.circle(s, c, (ex, ic[1]), 2)
        pygame.draw.line(s, c, (ic[0], ic[1]-hh), (ic[0], ic[1]-hh-5), 2)
        pygame.draw.circle(s, c, (ic[0], ic[1]-hh-6), 2)

    elif icon_type == 'people':
        # Two person silhouettes
        r = max(2, size // 4)
        for ox in [-r-2, r+2]:
            pygame.draw.circle(s, c, (ic[0]+ox, ic[1]-r-1), r, 2)
            pygame.draw.arc(s, c,
                            (ic[0]+ox-r, ic[1]-1, r*2, r*2), 0, math.pi, 2)

    elif icon_type == 'target':
        # Bullseye: 3 concentric rings + centre dot
        for ri in [size//2, size//3, size//6]:
            pygame.draw.circle(s, c, ic, ri, 1)
        pygame.draw.circle(s, c, ic, 2)

    elif icon_type == 'lightning':
        # Lightning bolt
        hs = size // 2
        pts = [(ic[0]+2,  ic[1]-hs),
               (ic[0]-hs//2, ic[1]+1),
               (ic[0]+hs//4, ic[1]+1),
               (ic[0]-2,  ic[1]+hs)]
        pygame.draw.lines(s, c, False, pts, 3)

    elif icon_type == 'back':
        # Left-pointing arrow
        hs = size // 2 - 1
        pygame.draw.line(s, c, (ic[0]+hs, ic[1]-hs), (ic[0]-hs, ic[1]), 2)
        pygame.draw.line(s, c, (ic[0]-hs, ic[1]), (ic[0]+hs, ic[1]+hs), 2)
        pygame.draw.line(s, c, (ic[0]-hs, ic[1]), (ic[0]+hs, ic[1]), 2)

    surface.blit(s, (cx - size - 3, cy - size - 3))


# ─── Professional Button ──────────────────────────────────────────────────────
class ProButton:
    """
    Premium button with:
     - Spring-eased hover scale
     - Glassmorphism fill
     - Neon left-edge bar
     - Icon + label layout
     - Ripple effect on click
    """

    def __init__(self, rect: pygame.Rect, label: str, icon: str,
                 accent: tuple, font_size: int = FONT_MEDIUM):
        self.rect      = rect
        self.label     = label
        self.icon      = icon
        self.accent    = accent
        self.font_size = font_size
        self.hovered   = False
        self.pressed   = False
        self._hover_v  = 0.0    # spring velocity
        self._hover_x  = 0.0    # spring position  0..1
        self._ripple_t = 0.0    # ripple life 0..1, counting DOWN
        self._ripple_pos = (0, 0)

    def update(self, mouse_pos, mouse_down: bool) -> bool:
        was_pressed  = self.pressed
        self.hovered = self.rect.collidepoint(mouse_pos)
        self.pressed = self.hovered and mouse_down

        # Spring toward target
        target = 1.0 if self.hovered else 0.0
        spring_k = 0.22
        spring_d = 0.72
        self._hover_v += (target - self._hover_x) * spring_k
        self._hover_v *= spring_d
        self._hover_x  = max(0.0, min(1.0, self._hover_x + self._hover_v))

        fired = was_pressed and not self.pressed and self.hovered
        if fired:
            self._ripple_t = 1.0
            self._ripple_pos = mouse_pos

        if self._ripple_t > 0:
            self._ripple_t = max(0.0, self._ripple_t - 0.045)

        return fired

    def draw(self, surface: pygame.Surface):
        t  = self._hover_x
        r  = self.rect.inflate(int(t * 4), int(t * 2))

        # ── Background: very subtle dark tint ────────────────────────────
        bg_s = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
        bg_s.fill((8, 12, 22, int(8 + 20 * t)))
        # Thin accent tint on hover only
        if t > 0.1:
            tint_s = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
            tint_s.fill((*self.accent[:3], int(10 * t)))
            bg_s.blit(tint_s, (0, 0))
        surface.blit(bg_s, r.topleft)

        # ── Border: 1px, accent color, dim at rest / brighter on hover ───
        border_a = int(30 + 120 * t)
        brd_s = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
        pygame.draw.rect(brd_s, (*self.accent[:3], border_a),
                         brd_s.get_rect(), 1, border_radius=10)
        surface.blit(brd_s, r.topleft)

        # ── Left accent bar: 2px, fades in on hover ───────────────────────
        if t > 0.05:
            bar_h = r.height - 14
            bar_s = pygame.Surface((2, bar_h), pygame.SRCALPHA)
            bar_a = int(180 * t)
            for yi in range(bar_h):
                fa = int(bar_a * math.sin(math.pi * yi / bar_h))
                bar_s.set_at((0, yi), (*self.accent[:3], fa))
                bar_s.set_at((1, yi), (*self.accent[:3], fa // 3))
            surface.blit(bar_s, (r.left + 5, r.top + 7))

        # ── Ripple on click ───────────────────────────────────────────────
        if self._ripple_t > 0:
            rt = 1.0 - self._ripple_t
            rip_r = int(rt * max(r.width, r.height) * 0.85)
            rip_a = int(45 * self._ripple_t)
            rip_s = pygame.Surface((rip_r * 2 + 2, rip_r * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(rip_s, (*self.accent[:3], rip_a),
                               (rip_r + 1, rip_r + 1), rip_r, 1)
            rx = self._ripple_pos[0] - rip_r - 1
            ry = self._ripple_pos[1] - rip_r - 1
            surface.blit(rip_s, (rx, ry), special_flags=pygame.BLEND_RGBA_ADD)

        # ── Text + icon layout ─────────────────────────────────────────────
        text_col   = COL_TEXT_PRI if t > 0.4 else COL_TEXT_SEC
        font_label = FontCache.get(self.font_size, bold=True)
        label_s    = font_label.render(self.label, True, text_col)

        # Icon is 14px box; total layout = [icon 14px] [8px gap] [label]
        icon_size = 14
        total_w   = icon_size * 2 + 8 + label_s.get_width()
        ix  = r.centerx - total_w // 2 + icon_size   # centre of icon
        lx  = ix + icon_size + 8
        ly  = r.centery - label_s.get_height() // 2

        icon_alpha = int(160 + 60 * t)
        draw_icon(surface, self.icon, ix, r.centery, icon_size,
                  self.accent, icon_alpha)
        surface.blit(label_s, (lx, ly))


# ─── Difficulty Selector ──────────────────────────────────────────────────────
class DifficultySelector:
    """Compact pill selector: ← [LABEL] →"""

    DIFF_LABELS  = ['EASY', 'MEDIUM', 'HARD', 'ADAPTIVE']
    DIFF_COLORS  = [COL_ACCENT_D, COL_ACCENT_C, COL_ACCENT_B, COL_ACCENT_A]

    def __init__(self, rect: pygame.Rect, index: int = 1):
        self.rect  = rect
        self.index = index
        self._prev_index = index
        self._anim_t = 1.0  # 0..1 transition
        self._dir    = 1

        bw = 40
        self._btn_l = pygame.Rect(rect.left, rect.top, bw, rect.height)
        self._btn_r = pygame.Rect(rect.right - bw, rect.top, bw, rect.height)
        self._pill  = pygame.Rect(rect.left + bw + 4, rect.top, rect.width - bw * 2 - 8, rect.height)

        self._hover_l   = False
        self._hover_r   = False
        self._was_down  = False   # for click-release detection

    def update(self, mouse_pos, mouse_down: bool) -> bool:
        self._hover_l = self._btn_l.collidepoint(mouse_pos)
        self._hover_r = self._btn_r.collidepoint(mouse_pos)

        # Advance transition animation
        if self._anim_t < 1.0:
            self._anim_t = min(1.0, self._anim_t + 0.12)

        # Click-release detection (fire on mouse-up, not hold)
        clicked = self._was_down and not mouse_down
        self._was_down = mouse_down

        changed = False
        if clicked and self._hover_l and self._anim_t >= 1.0:
            self._prev_index = self.index
            self.index = (self.index - 1) % 4
            self._anim_t = 0.0
            self._dir = -1
            changed = True
        elif clicked and self._hover_r and self._anim_t >= 1.0:
            self._prev_index = self.index
            self.index = (self.index + 1) % 4
            self._anim_t = 0.0
            self._dir = 1
            changed = True
        return changed

    def draw(self, surface: pygame.Surface):
        t = ease_out_cubic(self._anim_t)
        cur_col = self.DIFF_COLORS[self.index]

        # Arrow buttons
        for btn, sym, hov in [(self._btn_l, '‹', self._hover_l),
                               (self._btn_r, '›', self._hover_r)]:
            bg_a = 50 if hov else 20
            bg_s = pygame.Surface((btn.width, btn.height), pygame.SRCALPHA)
            bg_s.fill((*cur_col, bg_a))
            surface.blit(bg_s, btn.topleft)
            brd_s = pygame.Surface((btn.width, btn.height), pygame.SRCALPHA)
            pygame.draw.rect(brd_s, (*cur_col, 80 if hov else 40),
                             brd_s.get_rect(), 1, border_radius=8)
            surface.blit(brd_s, btn.topleft)
            f = FontCache.get(FONT_LARGE, bold=True)
            # pygame.font.render only accepts RGB (3-tuple)
            sym_col = tuple(int(c * (0.78 + 0.22 * int(hov))) for c in cur_col[:3])
            sym_s = f.render(sym, True, sym_col)
            sym_s.set_alpha(200 if hov else 140)
            surface.blit(sym_s, sym_s.get_rect(center=btn.center))

        # Pill background
        pill_s = pygame.Surface((self._pill.width, self._pill.height), pygame.SRCALPHA)
        pill_s.fill((*cur_col, int(18 + 8 * t)))
        surface.blit(pill_s, self._pill.topleft)
        prd_s = pygame.Surface((self._pill.width, self._pill.height), pygame.SRCALPHA)
        pygame.draw.rect(prd_s, (*cur_col, int(80 + 60 * t)),
                         prd_s.get_rect(), 1, border_radius=8)
        surface.blit(prd_s, self._pill.topleft)

        # Label floats ABOVE the pill — not cramped inside
        offset_x    = int((1 - t) * 20 * self._dir)
        label_alpha = int(255 * t)
        f2  = FontCache.get(FONT_SMALL, bold=True)
        lab_s = f2.render(self.DIFF_LABELS[self.index], True, cur_col[:3])
        lab_s.set_alpha(label_alpha)

        f3 = FontCache.get(FONT_TINY, bold=True)
        pre_s = f3.render("AI DIFFICULTY", True, (140, 155, 195))
        pre_s.set_alpha(200)
        surface.blit(pre_s, pre_s.get_rect(
            centerx=self._pill.centerx,
            bottom=self._pill.top - 5
        ))

        # Only the difficulty name, perfectly centred in pill
        cx_pill = self._pill.centerx + offset_x
        surface.blit(lab_s, lab_s.get_rect(
            center=(cx_pill, self._pill.centery)
        ))


# ─── Panel backdrop ───────────────────────────────────────────────────────────
def draw_glass_panel(surface: pygame.Surface, rect: pygame.Rect,
                     accent: tuple, alpha_base: int = 12, radius: int = 16):
    """Minimal glassmorphism: very subtle fill + single thin border."""
    s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    # Barely-visible tinted fill
    s.fill((10, 14, 26, alpha_base))
    # Single-pixel top highlight
    pygame.draw.line(s, (255, 255, 255, 6), (radius, 1), (rect.width - radius, 1), 1)
    surface.blit(s, rect.topleft)

    # Thin, dim border — 1px only
    brd = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(brd, (*accent[:3], 35), brd.get_rect(), 1, border_radius=radius)
    surface.blit(brd, rect.topleft)


# ─── Section heading helper ───────────────────────────────────────────────────
def draw_section_label(surface, text, cx, y, color=COL_TEXT_SEC):
    f = FontCache.get(FONT_TINY, bold=True)
    # Letter spacing simulation: render each char separately
    chars   = list(text)
    spacing = 3
    widths  = [f.render(c, True, color).get_width() + spacing for c in chars]
    total   = sum(widths) - spacing
    x = cx - total // 2
    for c, w in zip(chars, widths):
        cs = f.render(c, True, color)
        surface.blit(cs, (x, y - cs.get_height() // 2))
        x += w


# ─── Main Menu ────────────────────────────────────────────────────────────────
class MainMenu:
    # Layout constants
    _BTN_W  = 340
    _BTN_H  = 54
    _BTN_GAP = 10

    def __init__(self, sound_manager):
        self.sound   = sound_manager
        self._t      = 0.0
        self._sub    = 'main'   # 'main' | 'mode'

        self._particles = ParticleSystem()
        self._spawn_t   = 0

        # Entry animation
        self._entry_t   = 0.0   # 0..1 fade-in

        self._bg    = ProBackground()
        self._logo  = LogoRenderer()

        self._build_buttons()
        self._seed_particles()   # pre-fill background dots

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_buttons(self):
        cx = WINDOW_WIDTH // 2
        bw = self._BTN_W
        bh = self._BTN_H
        gap= self._BTN_GAP

        # ── Main panel ──────────────────────────────────────────────────────
        # Position below title area (title ends ~210px)
        panel_top = 235
        total_h   = 4 * bh + 3 * gap
        start_y   = panel_top + (WINDOW_HEIGHT - panel_top - 50 - total_h) // 2

        # icon types use draw_icon() — no Unicode glyphs needed
        icons  = ['play', 'settings', 'stats', 'quit']
        labels = ['PLAY', 'SETTINGS', 'STATISTICS', 'QUIT']
        colors = [COL_ACCENT_A, COL_ACCENT_B, COL_ACCENT_C, (200, 80, 80)]

        self._main_btns = []
        for i in range(4):
            y = start_y + i * (bh + gap)
            self._main_btns.append(
                ProButton(pygame.Rect(cx - bw // 2, y, bw, bh),
                          labels[i], icons[i], colors[i], FONT_MEDIUM)
            )
        self._main_panel_rect = pygame.Rect(
            cx - bw // 2 - 22, start_y - 18,
            bw + 44, total_h + 36
        )

        # ── Mode panel ──────────────────────────────────────────────────────
        mode_icons  = ['robot', 'people', 'target', 'lightning']
        mode_labels = ['VS AI', 'TWO PLAYERS', 'TRAINING', 'CHALLENGE']
        mode_total_h = 4 * bh + 3 * gap
        mode_start_y = panel_top + (WINDOW_HEIGHT - panel_top - 50 - mode_total_h - bh - gap - 52) // 2

        self._mode_btns = []
        for i in range(4):
            y = mode_start_y + i * (bh + gap)
            self._mode_btns.append(
                ProButton(pygame.Rect(cx - bw // 2, y, bw, bh),
                          mode_labels[i], mode_icons[i], MODE_COLORS[i], FONT_MEDIUM)
            )

        # Back button
        back_y = mode_start_y + 4 * (bh + gap) + 6
        self._back_btn = ProButton(
            pygame.Rect(cx - bw // 2, back_y, bw, bh - 8),
            'BACK', 'back', COL_TEXT_DIM, FONT_SMALL
        )

        # Difficulty selector
        diff_y = back_y + bh + 6
        diff_rect = pygame.Rect(cx - bw // 2, diff_y, bw, 52)
        self._diff_sel = DifficultySelector(diff_rect, index=1)

        mode_panel_bottom = diff_y + 52 + 14
        self._mode_panel_rect = pygame.Rect(
            cx - bw // 2 - 22, mode_start_y - 18,
            bw + 44, mode_panel_bottom - (mode_start_y - 18)
        )

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, dt: float, mouse_pos, mouse_down: bool):
        self._t += dt
        self._entry_t = min(1.0, self._entry_t + dt * 1.4)
        self._bg.update(dt)
        self._logo.update(dt)
        self._spawn_ambient()
        self._particles.update()

        if self._sub == 'main':
            return self._update_main(mouse_pos, mouse_down)
        return self._update_mode(mouse_pos, mouse_down)

    def _update_main(self, mouse_pos, mouse_down):
        actions = [
            lambda: self._switch_mode(),
            lambda: (STATE_SETTINGS, {}),
            lambda: (STATE_STATS,    {}),
            lambda: ('quit',         {}),
        ]
        for i, btn in enumerate(self._main_btns):
            if btn.update(mouse_pos, mouse_down):
                self.sound.play_menu_select()
                result = actions[i]()
                if result is not None:
                    return result
        return None

    def _switch_mode(self):
        self._sub = 'mode'
        # Reset mode button hover states
        for b in self._mode_btns:
            b._hover_x = 0.0

    def _update_mode(self, mouse_pos, mouse_down):
        modes = [MODE_VS_AI, MODE_TWO_PLAYER, MODE_TRAINING, MODE_CHALLENGE]
        changed = self._diff_sel.update(mouse_pos, mouse_down)
        if changed:
            self.sound.play_menu_hover()

        for i, btn in enumerate(self._mode_btns):
            if btn.update(mouse_pos, mouse_down):
                self.sound.play_menu_select()
                return (STATE_GAME, {
                    'mode': modes[i],
                    'difficulty': self._diff_sel.index
                })

        if self._back_btn.update(mouse_pos, mouse_down):
            self.sound.play_menu_select()
            self._sub = 'main'
            for b in self._main_btns:
                b._hover_x = 0.0
        return None

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface):
        self._bg.draw(surface)
        self._particles.draw(surface)
        self._logo.draw(surface)

        # Entry fade-in overlay
        entry_alpha = int(255 * (1.0 - ease_out_cubic(self._entry_t)))
        if entry_alpha > 0:
            fade_s = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
            fade_s.fill(COL_BG)
            fade_s.set_alpha(entry_alpha)
            surface.blit(fade_s, (0, 0))

        if self._sub == 'main':
            self._draw_main_panel(surface)
        else:
            self._draw_mode_panel(surface)

        self._draw_footer(surface)

    def _draw_main_panel(self, surface):
        cx = WINDOW_WIDTH // 2
        draw_glass_panel(surface, self._main_panel_rect, COL_ACCENT_A, 10, 16)

        # Panel section label
        draw_section_label(surface, "MENU",
                           cx, self._main_panel_rect.top + 10,
                           COL_TEXT_DIM)

        for btn in self._main_btns:
            btn.draw(surface)

    def _draw_mode_panel(self, surface):
        cx = WINDOW_WIDTH // 2
        draw_glass_panel(surface, self._mode_panel_rect, COL_ACCENT_B, 10, 16)

        # Panel label
        draw_section_label(surface, "SELECT GAME MODE",
                           cx, self._mode_panel_rect.top + 10,
                           COL_TEXT_DIM)

        for btn in self._mode_btns:
            btn.draw(surface)

        self._back_btn.draw(surface)
        self._diff_sel.draw(surface)

    def _draw_footer(self, surface: pygame.Surface):
        cx = WINDOW_WIDTH // 2
        fy = WINDOW_HEIGHT - 14

        f = FontCache.get(FONT_TINY)
        # Left: version
        v_s = f.render("v2.0", True, COL_TEXT_DIM)
        surface.blit(v_s, (16, fy - v_s.get_height() // 2))

        # Center: credits
        cr = f.render("Air Hockey Vision  ·  Hand Tracking Edition  ·  2025",
                      True, COL_TEXT_DIM)
        surface.blit(cr, cr.get_rect(centerx=cx, centery=fy))

        # Right: FPS-area left empty intentionally

    def _spawn_ambient(self):
        """Spawn visible colored floating dots across the whole screen."""
        self._spawn_t += 1
        # Faster spawn rate — every 3 frames
        if self._spawn_t % 3 == 0:
            colors = [COL_ACCENT_A, COL_ACCENT_B, COL_ACCENT_C, COL_ACCENT_D,
                      (180, 100, 255), (0, 180, 255), (255, 200, 50)]
            col = random.choice(colors)
            # Spawn across full width, all vertical positions
            self._particles._particles.append(
                Particle(
                    random.randint(30, WINDOW_WIDTH - 30),
                    random.randint(30, WINDOW_HEIGHT - 30),
                    (random.random() - 0.5) * 0.4,
                    (random.random() - 0.5) * 0.3 - 0.15,
                    col,
                    random.uniform(2.5, 5.0),   # visible size
                    random.randint(120, 220),    # longer life
                    gravity=0.0
                )
            )

    def _seed_particles(self):
        """Pre-fill the screen with dots so they appear immediately."""
        colors = [COL_ACCENT_A, COL_ACCENT_B, COL_ACCENT_C, COL_ACCENT_D]
        for _ in range(55):
            col = random.choice(colors)
            life = random.randint(60, 200)
            self._particles._particles.append(
                Particle(
                    random.randint(30, WINDOW_WIDTH - 30),
                    random.randint(30, WINDOW_HEIGHT - 30),
                    (random.random() - 0.5) * 0.35,
                    (random.random() - 0.5) * 0.25,
                    col,
                    random.uniform(2.5, 4.5),
                    life,
                    gravity=0.0
                )
            )
