r"""
Air Hockey Vision - Motion Smoother (One Euro Filter)
=====================================================
Implements a 2D adaptive low-pass filter (One Euro Filter) designed for 
real-time, low-latency human-computer interaction (HCI).

Mathematical Formulation:
-------------------------
The filter adapts its cutoff frequency based on the speed of the control signal,
balancing jitter reduction at rest with lag minimization during rapid movements.
For a series of values X_i measured at timestamps t_i:

1. Calculate the time step and instantaneous sampling rate:
   dt = t_i - t_{i-1}
   f  = 1 / dt

2. Compute the raw velocity (derivative):
   dX_i = (X_i - \hat{X}_{i-1}) * f

3. Apply a low-pass filter to the velocity:
   \alpha_{d} = 1 / (1 + \tau_d / dt)  where \tau_d = 1 / (2 * \pi * d_cutoff)
   \hat{dX}_i = \alpha_d * dX_i + (1 - \alpha_d) * \hat{dX}_{i-1}

4. Adapt the position filter's cutoff frequency based on speed:
   f_c = min_cutoff + \beta * |\hat{dX}_i|

5. Apply the low-pass filter to the position:
   \alpha_{p} = 1 / (1 + \tau_p / dt)  where \tau_p = 1 / (2 * \pi * f_c)
   \hat{X}_i   = \alpha_p * X_i + (1 - \alpha_p) * \hat{X}_{i-1}

References:
-----------
Casiez, G., Roussel, N., & Vogel, D. (2012). 1€ Filter: A Simple Algorithms for 
Filtering Noisy Input Signals in Real-Time Cloud-Based Interactive Systems.
In Proceedings of the SIGCHI Conference on Human Factors in Computing Systems 
(CHI '12), pp. 2527-2530. ACM. https://doi.org/10.1145/2207676.2208639
"""

import math
import time
from collections import deque


class _LowPassFilter:
    """
    A single-pole, first-order Infinite Impulse Response (IIR) low-pass filter.
    """

    def __init__(self):
        self._y = None
        self._a = 1.0

    def set_alpha(self, alpha: float):
        """Sets the smoothing factor alpha, clamped between 0.0 and 1.0."""
        self._a = max(0.0, min(1.0, alpha))

    def filter(self, value: float) -> float:
        """Applies the IIR filter step: y_i = a * x_i + (1-a) * y_{i-1}"""
        if self._y is None:
            self._y = value
        else:
            self._y = self._a * value + (1.0 - self._a) * self._y
        return self._y

    @property
    def last(self) -> float | None:
        """Returns the last filtered output value."""
        return self._y

    def reset(self):
        """Resets the internal state filter buffer."""
        self._y = None


class _OneEuroFilter:
    """
    Adaptive low-pass filter for a single scalar value.
    
    Attributes:
        freq (float): Nominal sampling frequency (Hz), updated dynamically.
        min_cutoff (float): Minimum cutoff frequency (Hz). Lower values reduce jitter at rest.
        beta (float): Speed coefficient. Higher values minimize lag during rapid motion.
        d_cutoff (float): Cutoff frequency for the derivative filter (Hz).
    """

    def __init__(self, freq: float, min_cutoff: float = 1.0,
                 beta: float = 0.0, d_cutoff: float = 1.0):
        self.freq = freq
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self._x_filt = _LowPassFilter()
        self._dx_filt = _LowPassFilter()
        self._last_time: float | None = None

    @staticmethod
    def _alpha(cutoff: float, freq: float) -> float:
        tau = 1.0 / (2.0 * math.pi * cutoff)
        te  = 1.0 / freq
        return 1.0 / (1.0 + tau / te)

    def filter(self, x: float, timestamp: float | None = None) -> float:
        now = timestamp if timestamp is not None else time.perf_counter()

        # Update frequency estimate from real timing
        if self._last_time is not None:
            elapsed = now - self._last_time
            if elapsed > 1e-6:
                self.freq = 0.9 * self.freq + 0.1 * (1.0 / elapsed)
        self._last_time = now

        # Derivative (speed of change)
        prev_x = self._x_filt.last
        dx = 0.0 if prev_x is None else (x - prev_x) * self.freq

        # Filter derivative
        self._dx_filt.set_alpha(self._alpha(self.d_cutoff, self.freq))
        edx = self._dx_filt.filter(dx)

        # Adaptive cutoff based on speed
        cutoff = self.min_cutoff + self.beta * abs(edx)

        # Filter position
        self._x_filt.set_alpha(self._alpha(cutoff, self.freq))
        return self._x_filt.filter(x)

    def reset(self):
        self._x_filt.reset()
        self._dx_filt.reset()
        self._last_time = None


# ── Public API: MotionSmoother ────────────────────────────────────────────────

class MotionSmoother:
    """
    2-D One Euro Filter for real-time hand tracking.

    Tuning guide
    ------------
    min_cutoff  : lower → smoother at rest, higher → more jitter at rest
    beta        : higher → faster response during fast movement
    d_cutoff    : derivative filter cutoff, usually left at 1.0

    Recommended presets
    -------------------
    "Mouse-like"    : min_cutoff=1.5, beta=0.12
    "Smooth"        : min_cutoff=0.8, beta=0.07
    "Raw (no lag)"  : min_cutoff=3.0, beta=0.25
    """

    # ── Tuning constants (mouse-like response) ────────────────────────────────
    MIN_CUTOFF = 1.2   # smoothing at rest (lower = smoother)
    BETA       = 0.15  # speed coefficient  (higher = faster response)
    D_CUTOFF   = 1.0   # derivative filter cutoff

    def __init__(self, alpha: float = 0.95):
        # `alpha` kept for backwards compat — ignored; we use One Euro instead
        freq = 60.0  # nominal 60 Hz camera
        self._fx = _OneEuroFilter(freq, self.MIN_CUTOFF, self.BETA, self.D_CUTOFF)
        self._fy = _OneEuroFilter(freq, self.MIN_CUTOFF, self.BETA, self.D_CUTOFF)

        # Velocity estimation (for physics prediction)
        self._history:    deque = deque(maxlen=5)
        self._timestamps: deque = deque(maxlen=5)
        self.velocity = (0.0, 0.0)
        self.quality  = 1.0

        self._smoothed: tuple | None = None
        self._prev:     tuple | None = None

    # ------------------------------------------------------------------
    def configure(self, smoothness: float):
        """
        Tune the filter from the settings slider.

        Higher smoothness calms jitter at rest. Lower smoothness keeps the hand
        closer to the raw camera position for more aggressive play.
        """
        s = max(0.0, min(1.0, float(smoothness)))
        min_cutoff = 2.2 - s * 1.45
        beta = 0.24 - s * 0.16

        self._fx.min_cutoff = min_cutoff
        self._fy.min_cutoff = min_cutoff
        self._fx.beta = beta
        self._fy.beta = beta

    def update(self, raw_pos: tuple) -> tuple:
        """Feed raw (x, y) in normalized [0,1] coords; returns filtered position."""
        now = time.perf_counter()

        sx = self._fx.filter(raw_pos[0], now)
        sy = self._fy.filter(raw_pos[1], now)
        self._smoothed = (sx, sy)

        # Velocity from windowed history
        self._history.append(self._smoothed)
        self._timestamps.append(now)

        if len(self._history) >= 2:
            p0 = self._history[0]
            p1 = self._history[-1]
            t0 = self._timestamps[0]
            t1 = self._timestamps[-1]
            elapsed = t1 - t0
            if elapsed > 1e-5:
                self.velocity = (
                    (p1[0] - p0[0]) / elapsed,
                    (p1[1] - p0[1]) / elapsed,
                )

        # Quality signal: drops on erratic large jumps
        if self._prev is not None:
            dx = raw_pos[0] - self._prev[0]
            dy = raw_pos[1] - self._prev[1]
            jump = math.hypot(dx, dy)
            # Normalized coords → jump of 0.05 is ~5% of frame, considered erratic
            self.quality = max(0.0, min(1.0, 1.0 - jump / 0.15))
        else:
            self.quality = 1.0

        self._prev = raw_pos
        return self._smoothed

    def predict(self, dt: float = 0.016) -> tuple | None:
        """Return a predicted position `dt` seconds ahead using current velocity."""
        if self._smoothed is None:
            return None
        vx, vy = self.velocity
        px = self._smoothed[0] + vx * dt
        py = self._smoothed[1] + vy * dt
        # Clamp to valid range
        return (max(0.0, min(1.0, px)), max(0.0, min(1.0, py)))

    def reset(self):
        self._fx.reset()
        self._fy.reset()
        self._history.clear()
        self._timestamps.clear()
        self.velocity = (0.0, 0.0)
        self.quality  = 1.0
        self._smoothed = None
        self._prev     = None
