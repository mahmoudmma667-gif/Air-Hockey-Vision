"""
Air Hockey Vision - Collision System
====================================
A sub-stepped circle-to-circle and boundary-restricted physics engine 
designed to handle high-velocity puck collisions with zero tunnelling.

Key Physical Models:
--------------------
1. Sub-Stepping (Temporal Discretisation):
   Splits each frame's visual time step (1/60s) into `PHYSICS_SUBSTEPS` (default: 4)
   smaller intervals. This reduces the positional displacement per step, ensuring
   collisions are detected at precise contact points even when the puck speed
   exceeds its own radius per frame (preventing wall/paddle tunnelling).

2. Circle-to-Circle Collision Resolution:
   Puck-to-paddle collisions are solved by finding the relative position vector
   and contact depth. The puck is translated along the normal to resolve overlap.
   The post-collision velocity is calculated using:
     v'_puck = v_puck - (1 + e) * (v_rel . n) * n + k * v_paddle
   where `e` is the coefficient of restitution (elasticity) and `k` is the momentum
   transfer factor representing kinetic friction and energy transfer from the paddle.
"""

import math
from src.core.settings import (
    PUCK_RESTITUTION, PHYSICS_SUBSTEPS,
    TABLE_LEFT, TABLE_RIGHT, TABLE_TOP, TABLE_BOTTOM,
    TABLE_CENTER_Y, GOAL_HALF, PUCK_MAX_SPEED,
)
from src.utils.math_utils import circle_circle_collision, vec2_length
from src.core.events import bus, EVT_PUCK_HIT_WALL, EVT_PUCK_HIT_PADDLE, EVT_GOAL_SCORED


class CollisionSystem:
    """
    Orchestrates physics state updates across time-slices (substeps).
    
    Responsible for checking and resolving puck-boundary, puck-goal,
    and puck-paddle collisions using impulse dynamics.
    """

    def update(self, puck, paddles: list) -> str | None:
        """
        Returns 'p1' or 'p2' if a goal was scored this frame, else None.
        """
        dt = 1.0 / PHYSICS_SUBSTEPS
        goal = None

        for _ in range(PHYSICS_SUBSTEPS):
            puck.x += puck.vx * dt
            puck.y += puck.vy * dt

            hit_wall = self._check_walls(puck)
            if hit_wall:
                bus.emit(EVT_PUCK_HIT_WALL, side=hit_wall)

            for paddle in paddles:
                if self._check_paddle(puck, paddle):
                    bus.emit(EVT_PUCK_HIT_PADDLE, paddle_id=paddle.player_id)

            g = self._check_goal(puck)
            if g:
                goal = g
                break

        return goal

    # ── Internal ──────────────────────────────────────────────────────────────

    def _check_walls(self, puck) -> str | None:
        r   = puck.radius
        hit = None

        if puck.y - r < TABLE_TOP:
            puck.y  = TABLE_TOP + r
            puck.vy = abs(puck.vy) * PUCK_RESTITUTION
            hit = 'top'

        elif puck.y + r > TABLE_BOTTOM:
            puck.y  = TABLE_BOTTOM - r
            puck.vy = -abs(puck.vy) * PUCK_RESTITUTION
            hit = 'bottom'

        if puck.x - r < TABLE_LEFT:
            # Check if inside goal mouth (left)
            if abs(puck.y - TABLE_CENTER_Y) < GOAL_HALF:
                pass   # goal – don't bounce
            else:
                puck.x  = TABLE_LEFT + r
                puck.vx = abs(puck.vx) * PUCK_RESTITUTION
                hit = 'left'

        elif puck.x + r > TABLE_RIGHT:
            # Check if inside goal mouth (right)
            if abs(puck.y - TABLE_CENTER_Y) < GOAL_HALF:
                pass   # goal – don't bounce
            else:
                puck.x  = TABLE_RIGHT - r
                puck.vx = -abs(puck.vx) * PUCK_RESTITUTION
                hit = 'right'

        return hit

    def _check_paddle(self, puck, paddle) -> bool:
        colliding, normal, depth = circle_circle_collision(
            puck.pos, puck.radius, paddle.pos, paddle.radius
        )
        if not colliding:
            return False

        # Separate circles
        puck.x += normal[0] * depth
        puck.y += normal[1] * depth

        paddle_vel = paddle.smoothed_velocity
        rel_vx = puck.vx - paddle_vel[0]
        rel_vy = puck.vy - paddle_vel[1]
        rel_dot = rel_vx * normal[0] + rel_vy * normal[1]

        if rel_dot < 0:
            impulse = -(1.0 + PUCK_RESTITUTION) * rel_dot
            puck.vx += impulse * normal[0]
            puck.vy += impulse * normal[1]

            # Transfer paddle momentum
            puck.vx += paddle_vel[0] * 0.65
            puck.vy += paddle_vel[1] * 0.65

            # Cap speed
            spd = vec2_length((puck.vx, puck.vy))
            if spd > PUCK_MAX_SPEED:
                s = PUCK_MAX_SPEED / spd
                puck.vx *= s
                puck.vy *= s

        return True

    def _check_goal(self, puck) -> str | None:
        """
        'p1' = P1 scored (puck went into right goal / P2's end)
        'p2' = P2 scored (puck went into left goal / P1's end)
        """
        r = puck.radius

        # Right goal → P1 scores
        if puck.x + r >= TABLE_RIGHT and abs(puck.y - TABLE_CENTER_Y) < GOAL_HALF:
            return 'p1'

        # Left goal → P2 scores
        if puck.x - r <= TABLE_LEFT and abs(puck.y - TABLE_CENTER_Y) < GOAL_HALF:
            return 'p2'

        return None
