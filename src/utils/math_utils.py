"""
Air Hockey Vision - Math Utilities
Fast 2D vector helpers using NumPy.
"""

import math
import numpy as np


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def vec2_length(v) -> float:
    return math.hypot(v[0], v[1])


def vec2_normalize(v):
    length = vec2_length(v)
    if length < 1e-9:
        return (0.0, 0.0)
    return (v[0] / length, v[1] / length)


def vec2_dot(a, b) -> float:
    return a[0] * b[0] + a[1] * b[1]


def vec2_scale(v, s):
    return (v[0] * s, v[1] * s)


def vec2_add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def vec2_sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def vec2_dist(a, b) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def vec2_lerp(a, b, t: float):
    return (lerp(a[0], b[0], t), lerp(a[1], b[1], t))


def reflect(velocity, normal):
    """Reflect velocity vector off a surface with given normal."""
    dot = vec2_dot(velocity, normal)
    return (
        velocity[0] - 2 * dot * normal[0],
        velocity[1] - 2 * dot * normal[1],
    )


def circle_circle_collision(pos_a, r_a: float, pos_b, r_b: float):
    """
    Returns (colliding: bool, normal: tuple, depth: float)
    normal points from b to a.
    """
    dx = pos_a[0] - pos_b[0]
    dy = pos_a[1] - pos_b[1]
    dist_sq = dx * dx + dy * dy
    min_dist = r_a + r_b
    if dist_sq < min_dist * min_dist:
        dist = math.sqrt(dist_sq) if dist_sq > 1e-9 else 1e-5
        nx = dx / dist
        ny = dy / dist
        depth = min_dist - dist
        return True, (nx, ny), depth
    return False, (0.0, 0.0), 0.0


def predict_puck_position(pos, vel, steps: int):
    """Simple linear puck position prediction (ignores walls)."""
    return (pos[0] + vel[0] * steps, pos[1] + vel[1] * steps)
