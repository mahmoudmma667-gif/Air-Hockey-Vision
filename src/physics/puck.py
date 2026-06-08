"""
Air Hockey Vision - Puck Physics (updated)
Puck with friction, max speed, trail.
"""

import random
import math
from src.core.settings import (
    PUCK_RADIUS, PUCK_FRICTION, PUCK_MAX_SPEED, PUCK_MIN_SPEED,
    PUCK_RESTITUTION, TABLE_LEFT, TABLE_RIGHT, TABLE_TOP, TABLE_BOTTOM,
    TABLE_CENTER_X, TABLE_CENTER_Y, TRAIL_LENGTH,
)
from src.utils.math_utils import vec2_length


class Puck:
    def __init__(self):
        self.x: float  = float(TABLE_CENTER_X)
        self.y: float  = float(TABLE_CENTER_Y)
        self.vx: float = 0.0
        self.vy: float = 0.0
        self.radius    = PUCK_RADIUS
        self.trail: list[tuple] = []
        self.spin: float = 0.0
        self.active: bool = True
        self.spawn_scale: float = 1.0

    def reset(self, serve_to: int = 1):
        self.x  = float(TABLE_CENTER_X)
        self.y  = float(TABLE_CENTER_Y)
        self.trail.clear()
        self.spin   = 0.0
        self.active = True
        self.spawn_scale = 4.0  # Starts 4x larger for drop-in effect


        angle     = random.uniform(-20, 20)
        speed     = 3.5  # Slower initial speed
        rad       = math.radians(angle)
        direction = 1 if serve_to == 1 else -1
        self.vx   = math.cos(rad) * speed * direction
        self.vy   = math.sin(rad) * speed

    @property
    def pos(self) -> tuple:
        return (self.x, self.y)

    @property
    def vel(self) -> tuple:
        return (self.vx, self.vy)

    @property
    def speed(self) -> float:
        return vec2_length((self.vx, self.vy))
