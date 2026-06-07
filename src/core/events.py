"""
Air Hockey Vision - Event System
Lightweight pub/sub event bus for decoupled communication.
"""

from collections import defaultdict
from typing import Callable, Any


class EventBus:
    """Simple synchronous event bus."""

    def __init__(self):
        self._listeners: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event: str, callback: Callable) -> None:
        self._listeners[event].append(callback)

    def unsubscribe(self, event: str, callback: Callable) -> None:
        try:
            self._listeners[event].remove(callback)
        except ValueError:
            pass

    def emit(self, event: str, **kwargs) -> None:
        for cb in list(self._listeners[event]):
            cb(**kwargs)

    def clear(self) -> None:
        self._listeners.clear()


# Global singleton bus
bus = EventBus()

# ─── Event Names ─────────────────────────────────────────────────────────────
EVT_GOAL_SCORED      = "goal_scored"
EVT_PUCK_HIT_WALL    = "puck_hit_wall"
EVT_PUCK_HIT_PADDLE  = "puck_hit_paddle"
EVT_GAME_OVER        = "game_over"
EVT_SCORE_CHANGED    = "score_changed"
EVT_STATE_CHANGE     = "state_change"
EVT_TIMER_TICK       = "timer_tick"
EVT_SETTINGS_CHANGED = "settings_changed"
EVT_PAUSE_TOGGLE     = "pause_toggle"
