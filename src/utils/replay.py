"""
Air Hockey Vision - Replay System
Records game state snapshots for instant replay.
"""

from collections import deque
from dataclasses import dataclass, field


@dataclass
class ReplayFrame:
    puck_x: float
    puck_y: float
    puck_vx: float
    puck_vy: float
    p1_x: float
    p1_y: float
    p2_x: float
    p2_y: float
    p1_score: int
    p2_score: int
    timestamp: float


class ReplayRecorder:
    """Circular buffer that stores the last N seconds of game frames."""

    def __init__(self, max_seconds: float = 5.0, fps: int = 60):
        maxlen = int(max_seconds * fps)
        self._buffer: deque[ReplayFrame] = deque(maxlen=maxlen)
        self._recording = True

    def record(self, puck, paddle1, paddle2, p1_score: int, p2_score: int,
               timestamp: float):
        if not self._recording:
            return
        self._buffer.append(ReplayFrame(
            puck_x=puck.x, puck_y=puck.y,
            puck_vx=puck.vx, puck_vy=puck.vy,
            p1_x=paddle1.x, p1_y=paddle1.y,
            p2_x=paddle2.x, p2_y=paddle2.y,
            p1_score=p1_score, p2_score=p2_score,
            timestamp=timestamp,
        ))

    def get_replay(self) -> list[ReplayFrame]:
        return list(self._buffer)

    def clear(self):
        self._buffer.clear()

    def pause(self):
        self._recording = False

    def resume(self):
        self._recording = True
