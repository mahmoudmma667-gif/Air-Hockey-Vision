"""
Air Hockey Vision - AI Paddle Controller
========================================
Implements a predictive artificial intelligence agent that simulates puck 
trajectories in real-time, executing defense and attacking maneuvers.

Key Algorithms & Systems:
-------------------------
1. Raycast Trajectory Simulation (Wall-Bounce Prediction):
   When the puck is moving towards the AI's zone, the controller simulates the 
   puck's future path. It step-integrates position (x_t = x_{t-1} + v_x) and reflects 
   velocity (v_y = -v_y * e) when boundary wall bounds are crossed. The simulation is 
   bounded to a maximum of `_MAX_SIM_STEPS` (120 ticks) to guarantee constant-time 
   execution (O(1)) and prevent infinite loops.

2. Geometric Attack Aiming Vector:
   If an attack is decided, the AI calculates a target goal corner (top/bottom corners
   of the player's goal mouth). It positions the paddle behind the predicted 
   interception point (ix, iy) with a spatial offset that aligns the collision 
   normal vector towards the selected corner, redirecting the puck dynamically.

3. Human-like Latency and Noise Modeling:
   - Reaction Delay: Recomputes the targeted interception point at a frequency 
     determined by the difficulty level (e.g. 250ms for Easy, 40ms for Hard).
   - Gaussian Noise: Adds random jitter using normal distribution models scaled 
     by difficulty-specific error magnitudes, ensuring the AI behaves realistically.
"""

import math
import random
import time

from src.core.settings import (
    TABLE_LEFT, TABLE_RIGHT, TABLE_TOP, TABLE_BOTTOM,
    TABLE_CENTER_X, TABLE_CENTER_Y,
    PUCK_RESTITUTION, AI_DIFFICULTY_HARD,
    GOAL_HALF,
)
from src.ai.difficulty import DifficultyProfile
from src.utils.math_utils import clamp, lerp, vec2_dist


# --- Simulation Constants ---
_MAX_SIM_STEPS = 120        # Upper bound on trajectory raycast steps
_SLOWDOWN_THRESHOLD = 0.3   # Linear speed threshold below which puck is stationary


class AIPaddle:
    """
    Predictive AI striker agent that tracks and intercept the puck.
    
    Attributes:
        paddle (Paddle): The physical paddle controlled by this AI.
        profile (DifficultyProfile): Tunable AI parameters for latency and precision.
    """

    def __init__(self, paddle, difficulty_level: int):
        self.paddle  = paddle
        self.profile = DifficultyProfile(difficulty_level)

        self._target_x = float(TABLE_CENTER_X + 150)
        self._target_y = float(TABLE_CENTER_Y)

        self._last_reaction_time = time.perf_counter()
        self._cached_target      = None   # held during reaction delay window

        self._jitter_phase = 0.0          # smooth micro-movement phase
        self._state        = 'defend'     # 'defend' | 'attack'

        # Attack state — where we want to push the puck
        self._attack_aim_y = float(TABLE_CENTER_Y)

    # ── Public ────────────────────────────────────────────────────────────────

    def update(self, puck, dt: float = 1 / 60):
        """Called every frame; moves the AI paddle toward its target."""
        now = time.perf_counter()

        # Recompute target only after reaction delay expires
        if now - self._last_reaction_time >= self.profile.reaction_delay:
            self._last_reaction_time = now
            self._cached_target = self._compute_target(puck)

        # Use cached target or fallback
        if self._cached_target:
            tx, ty = self._cached_target
        else:
            tx = TABLE_CENTER_X + self.paddle.radius + 90
            ty = self.paddle.y

        # ── Add human-like jitter / position error ────────────────────────
        error = self.profile.error_mag
        self._jitter_phase += dt * 3.5
        jx = math.sin(self._jitter_phase) * error * 0.35
        jy = math.cos(self._jitter_phase * 1.3) * error * 0.20
        tx += jx + random.gauss(0, error * 0.12)
        ty += jy + random.gauss(0, error * 0.08)

        # ── Clamp to AI's half of the table (right side) ─────────────────
        tx = clamp(tx, TABLE_CENTER_X + self.paddle.radius,
                   TABLE_RIGHT  - self.paddle.radius)
        ty = clamp(ty, TABLE_TOP    + self.paddle.radius,
                   TABLE_BOTTOM - self.paddle.radius)

        # ── Move toward target at max speed ──────────────────────────────
        dx   = tx - self.paddle.x
        dy   = ty - self.paddle.y
        dist = math.hypot(dx, dy)

        if dist > 0.5:
            step  = min(dist, self.profile.max_speed)
            new_x = self.paddle.x + (dx / dist) * step
            new_y = self.paddle.y + (dy / dist) * step
            self.paddle.move_to(new_x, new_y)

    def set_difficulty(self, level: int):
        self.profile = DifficultyProfile(level)

    def adapt_score(self, ai_score: int, player_score: int):
        self.profile.adapt(ai_score, player_score)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _compute_target(self, puck) -> tuple:
        """Decide where the AI paddle should move this tick."""
        px,  py  = puck.x,  puck.y
        pvx, pvy = puck.vx, puck.vy
        speed = math.hypot(pvx, pvy)

        # ── Is the puck actually moving toward our side? ──────────────────
        puck_coming = pvx > _SLOWDOWN_THRESHOLD

        if puck_coming and self.profile.can_attack:
            intercept = self._predict_intercept(puck)
            if intercept:
                ix, iy = intercept
                self._state = 'attack'

                if random.random() < self.profile.shoot_chance:
                    # Pick an attack aim point: top or bottom of opponent's goal
                    self._attack_aim_y = (
                        TABLE_TOP    + GOAL_HALF * 0.4
                        if random.random() > 0.5 else
                        TABLE_BOTTOM - GOAL_HALF * 0.4
                    )
                    # Position paddle BEHIND the intercept point, offset
                    # toward the aim, so the collision deflects puck that way.
                    dy_aim = self._attack_aim_y - iy
                    offset_y = clamp(dy_aim * 0.25, -self.paddle.radius * 0.8,
                                     self.paddle.radius * 0.8)
                    return (ix, iy + offset_y)

                # Simple intercept: just meet the puck
                return (ix, iy)

        # ── Defend: hold position in front of goal, track puck Y ─────────
        self._state  = 'defend'
        defend_x     = TABLE_RIGHT - 110
        # Track puck Y — tightness scales with difficulty
        track_alpha  = self.profile.defense_track_alpha
        target_y     = lerp(self.paddle.y, py, track_alpha)
        return (defend_x, target_y)

    # ─────────────────────────────────────────────────────────────────────────

    def _predict_intercept(self, puck) -> tuple | None:
        """
        Simulate the puck's path forward, accounting for wall bounces.
        Returns (x, y) where the AI should meet the puck, or None if
        the puck is predicted to stay on the player's side.

        Hard-capped at _MAX_SIM_STEPS to guarantee termination.
        """
        sim_x,  sim_y  = puck.x,  puck.y
        sim_vx, sim_vy = puck.vx, puck.vy
        r = puck.radius

        for step in range(_MAX_SIM_STEPS):
            sim_x += sim_vx
            sim_y += sim_vy

            # ── Top / Bottom wall bounces ─────────────────────────────────
            if sim_y - r < TABLE_TOP:
                sim_y  = TABLE_TOP + r
                sim_vy = abs(sim_vy) * PUCK_RESTITUTION
            elif sim_y + r > TABLE_BOTTOM:
                sim_y  = TABLE_BOTTOM - r
                sim_vy = -abs(sim_vy) * PUCK_RESTITUTION

            # ── Right wall (AI's back wall) ───────────────────────────────
            if sim_x + r > TABLE_RIGHT:
                sim_x  = TABLE_RIGHT - r
                sim_vx = -abs(sim_vx) * PUCK_RESTITUTION

            # ── Puck crossed center → can no longer intercept ─────────────
            if sim_x - r < TABLE_CENTER_X:
                return None

            # ── Puck is now in AI's zone and we have enough steps ─────────
            # Only intercept once we're past a minimum look-ahead
            if step >= max(5, self.profile.predict_steps // 4):
                if sim_x > TABLE_CENTER_X:
                    return (sim_x, sim_y)

        # End of simulation: if puck is still on AI side, return final pos
        if sim_x > TABLE_CENTER_X:
            return (sim_x, sim_y)
        return None
