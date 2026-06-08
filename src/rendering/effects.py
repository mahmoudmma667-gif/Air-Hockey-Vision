"""
Air Hockey Vision - Particle Effects & Visual FX
Neon glows, trails, goal explosions, and particle systems.
"""

import math
import random
import pygame
from src.core.settings import (
    C_PARTICLE_GOAL, GOAL_PARTICLE_COUNT, TRAIL_FADE_FACTOR,
    C_NEON_CYAN, C_NEON_MAGENTA, C_NEON_YELLOW,
)

_CIRCLE_SURFACE_CACHE: dict[tuple, pygame.Surface] = {}


def _cached_circle_surface(color, radius: int, alpha: int) -> pygame.Surface | None:
    radius = max(1, int(radius))
    alpha = max(0, min(255, int(alpha)))
    if alpha <= 0:
        return None

    alpha = min(255, max(32, ((alpha + 16) // 32) * 32))
    key = (*color[:3], radius, alpha)
    surf = _CIRCLE_SURFACE_CACHE.get(key)
    if surf is None:
        if len(_CIRCLE_SURFACE_CACHE) > 4096:
            _CIRCLE_SURFACE_CACHE.clear()
        size = radius * 2 + 1
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*color[:3], alpha), (radius, radius), radius)
        _CIRCLE_SURFACE_CACHE[key] = surf
    return surf


# ─── Glow helper ─────────────────────────────────────────────────────────────

def draw_glow_circle(surface: pygame.Surface, color, center, radius: int,
                     intensity: int = 3):
    """
    Draw a soft neon glow by rendering concentric circles with
    decreasing alpha.  Uses a temporary surface for blending.
    """
    max_r = radius + intensity * 8
    glow_surf = pygame.Surface((max_r * 2, max_r * 2), pygame.SRCALPHA)

    for i in range(intensity, 0, -1):
        r = radius + i * 8
        alpha = int(70 / i)
        c = (*color[:3], alpha)
        pygame.draw.circle(glow_surf, c, (max_r, max_r), r)

    pygame.draw.circle(glow_surf, (*color[:3], 220), (max_r, max_r), radius)
    # Bright core
    core_r = max(2, radius // 3)
    pygame.draw.circle(glow_surf, (255, 255, 255, 180), (max_r, max_r), core_r)

    surface.blit(glow_surf, (center[0] - max_r, center[1] - max_r),
                 special_flags=pygame.BLEND_RGBA_ADD)


def draw_glow_line(surface: pygame.Surface, color, start, end,
                   width: int = 2, glow_width: int = 8):
    """Draw a line with a neon glow halo."""
    glow_color = (*color[:3], 40)
    for w in range(glow_width, 0, -2):
        alpha = int(60 * (1 - w / glow_width))
        c = (*color[:3], alpha)
        pygame.draw.line(surface, c, start, end, w + width)
    pygame.draw.line(surface, color, start, end, width)


# ─── Particle ────────────────────────────────────────────────────────────────

class Particle:
    __slots__ = ('x', 'y', 'vx', 'vy', 'life', 'max_life',
                 'color', 'size', 'gravity')

    def __init__(self, x, y, vx, vy, color, size, life, gravity=0.08):
        self.x, self.y  = float(x), float(y)
        self.vx, self.vy = vx, vy
        self.color  = color
        self.size   = size
        self.life   = life
        self.max_life = life
        self.gravity  = gravity

    def update(self) -> bool:
        self.x  += self.vx
        self.y  += self.vy
        self.vy += self.gravity
        self.vx *= 0.97
        self.life -= 1
        return self.life > 0

    def draw(self, surface: pygame.Surface):
        if self.life <= 0:
            return
        alpha = int(255 * (self.life / self.max_life))
        r     = max(1, int(self.size * (self.life / self.max_life)))
        s = _cached_circle_surface(self.color, r, alpha)
        if s:
            surface.blit(s, (int(self.x) - r, int(self.y) - r),
                         special_flags=pygame.BLEND_RGBA_ADD)


# ─── Particle System ─────────────────────────────────────────────────────────

class ParticleSystem:
    """Manages a pool of particles."""

    def __init__(self):
        self._particles: list[Particle] = []

    def spawn_goal_explosion(self, x: float, y: float, scorer_id: int):
        """Burst of coloured sparks for goal celebration."""
        colors = C_PARTICLE_GOAL
        for _ in range(GOAL_PARTICLE_COUNT):
            angle   = random.uniform(0, math.tau)
            speed   = random.uniform(2, 12)
            vx      = math.cos(angle) * speed
            vy      = math.sin(angle) * speed
            color   = random.choice(colors)
            size    = random.uniform(3, 8)
            life    = random.randint(30, 70)
            self._particles.append(Particle(x, y, vx, vy, color, size, life))

    def spawn_hit_sparks(self, x: float, y: float, color, count: int = 12):
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(1, 5)
            vx    = math.cos(angle) * speed
            vy    = math.sin(angle) * speed
            size  = random.uniform(2, 4)
            life  = random.randint(8, 20)
            self._particles.append(Particle(x, y, vx, vy, color, size, life, gravity=0.12))

    def spawn_score_burst(self, x: float, y: float, color, count: int = 18):
        """Tiny fast sparks for score celebration — biased upward."""
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(2, 8)
            self._particles.append(Particle(
                x, y,
                math.cos(angle) * speed,
                math.sin(angle) * speed - 3.5,
                color,
                random.uniform(2, 5),
                random.randint(14, 30),
                gravity=0.2,
            ))

    def update(self):
        self._particles = [p for p in self._particles if p.update()]

    def draw(self, surface: pygame.Surface):
        for p in self._particles:
            p.draw(surface)

    def clear(self):
        self._particles.clear()

    @property
    def count(self) -> int:
        return len(self._particles)


# ─── Trail Renderer ───────────────────────────────────────────────────────────

def draw_trail(surface: pygame.Surface, trail: list, color,
               max_radius: int = 12):
    """Draw a fading speed trail."""
    n = len(trail)
    if n < 2:
        return
    for i, pos in enumerate(trail):
        t     = i / n
        alpha = int(180 * t * TRAIL_FADE_FACTOR)
        r     = max(2, int(max_radius * t * 0.7))
        s = _cached_circle_surface(color, r, alpha)
        if s:
            surface.blit(s, (int(pos[0]) - r, int(pos[1]) - r),
                         special_flags=pygame.BLEND_RGBA_ADD)


# ─── Screen Flash ─────────────────────────────────────────────────────────────

class ScreenFlash:
    def __init__(self):
        self.alpha    = 0
        self.color    = (255, 255, 255)
        self.decay    = 12
        self._surface: pygame.Surface | None = None
        self._size: tuple[int, int] | None = None

    def trigger(self, color=(255, 255, 255), strength: int = 180):
        self.color = color
        self.alpha = strength

    def update(self):
        if self.alpha > 0:
            self.alpha = max(0, self.alpha - self.decay)

    def draw(self, surface: pygame.Surface):
        if self.alpha <= 0:
            return
        w, h  = surface.get_size()
        if self._surface is None or self._size != (w, h):
            self._surface = pygame.Surface((w, h), pygame.SRCALPHA)
            self._size = (w, h)
        self._surface.fill((*self.color[:3], self.alpha))
        surface.blit(self._surface, (0, 0))


# ─── Screen Shake ─────────────────────────────────────────────────────────────

class ScreenShake:
    """Fast-decaying random screen offset for impact / vibration feedback."""

    def __init__(self):
        self._amp    = 0
        self._frames = 0
        self._total  = 15

    def trigger(self, amplitude: int = 8, frames: int = 15):
        self._amp    = max(self._amp, amplitude)
        self._frames = max(self._frames, frames)
        self._total  = max(self._total, frames)

    def update(self) -> tuple[int, int]:
        if self._frames <= 0:
            self._amp   = 0
            self._total = 15
            return (0, 0)
        frac = self._frames / max(1, self._total)
        amp  = max(1, int(self._amp * frac * frac))   # quadratic ease-out
        self._frames -= 1
        return (random.randint(-amp, amp), random.randint(-amp, amp))

    @property
    def active(self) -> bool:
        return self._frames > 0
