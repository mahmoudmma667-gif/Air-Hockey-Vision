"""
Air Hockey Vision - Paddle Physics (updated for new settings)
"""

from collections import deque
from src.core.settings import (
    PADDLE_RADIUS,
    TABLE_LEFT, TABLE_RIGHT, TABLE_TOP, TABLE_BOTTOM,
    TABLE_CENTER_X, TABLE_CENTER_Y, TRAIL_LENGTH,
)
from src.utils.math_utils import clamp, vec2_length


class Paddle:
    def __init__(self, player_id: int, color):
        self.player_id = player_id
        self.color     = color
        self.radius    = PADDLE_RADIUS

        if player_id == 1:          # left half
            self.x = float(TABLE_CENTER_X - 150)
            self.y = float(TABLE_CENTER_Y)
            self._x_min = TABLE_LEFT
            self._x_max = TABLE_CENTER_X
            self._y_min = TABLE_TOP
            self._y_max = TABLE_BOTTOM
        else:                       # right half
            self.x = float(TABLE_CENTER_X + 150)
            self.y = float(TABLE_CENTER_Y)
            self._x_min = TABLE_CENTER_X
            self._x_max = TABLE_RIGHT
            self._y_min = TABLE_TOP
            self._y_max = TABLE_BOTTOM

        self.vx: float = 0.0
        self.vy: float = 0.0
        self._vel_history: deque = deque(maxlen=4)
        self.trail: list[tuple]  = []
        self.active = True

    def move_to(self, tx: float, ty: float):
        tx = clamp(tx, self._x_min + self.radius, self._x_max - self.radius)
        ty = clamp(ty, self._y_min + self.radius, self._y_max - self.radius)

        self.vx = tx - self.x
        self.vy = ty - self.y
        self._vel_history.append((self.vx, self.vy))

        self.x = tx
        self.y = ty

        self.trail.append((self.x, self.y))
        if len(self.trail) > TRAIL_LENGTH // 2:
            self.trail.pop(0)

    @property
    def smoothed_velocity(self) -> tuple:
        if not self._vel_history:
            return (0.0, 0.0)
        ax = sum(v[0] for v in self._vel_history) / len(self._vel_history)
        ay = sum(v[1] for v in self._vel_history) / len(self._vel_history)
        return (ax, ay)

    @property
    def pos(self) -> tuple:
        return (self.x, self.y)

    @property
    def speed(self) -> float:
        return vec2_length((self.vx, self.vy))
