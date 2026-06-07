"""
Air Hockey Vision - Test Suite
==============================
Automated tests verifying core modules using Pytest.
Covers vector mathematics, dynamic filters, physics collisions, 
AI difficulty profiles, and replay buffers.
"""

import pytest
import math
import time

# Import subsystems to test
from src.utils.math_utils import (
    clamp, vec2_length, vec2_normalize, vec2_dot,
    vec2_scale, vec2_add, vec2_sub, vec2_dist,
    lerp, vec2_lerp, reflect, circle_circle_collision
)
from src.ai.difficulty import DifficultyProfile
from src.vision.smoother import MotionSmoother
from src.utils.replay import ReplayRecorder, ReplayFrame
from src.physics.puck import Puck
from src.physics.paddle import Paddle
from src.physics.collision import CollisionSystem
from src.core.settings import (
    TABLE_LEFT, TABLE_RIGHT, TABLE_TOP, TABLE_BOTTOM,
    TABLE_CENTER_X, TABLE_CENTER_Y, GOAL_HALF
)


# ==============================================================================
# 1. MATH UTILITIES TESTS
# ==============================================================================

def test_clamp():
    assert clamp(5.0, 0.0, 10.0) == 5.0
    assert clamp(-2.0, 0.0, 10.0) == 0.0
    assert clamp(15.0, 0.0, 10.0) == 10.0


def test_vec2_length():
    assert vec2_length((3.0, 4.0)) == pytest.approx(5.0)
    assert vec2_length((0.0, 0.0)) == 0.0


def test_vec2_normalize():
    n = vec2_normalize((3.0, 4.0))
    assert n[0] == pytest.approx(0.6)
    assert n[1] == pytest.approx(0.8)
    
    # Zero vector case
    assert vec2_normalize((0.0, 0.0)) == (0.0, 0.0)


def test_vec2_dot():
    assert vec2_dot((1.0, 2.0), (3.0, 4.0)) == 11.0


def test_vec2_scale():
    assert vec2_scale((2.0, 3.0), 3.0) == (6.0, 9.0)


def test_vec2_add_and_sub():
    assert vec2_add((1.0, 2.0), (3.0, 4.0)) == (4.0, 6.0)
    assert vec2_sub((5.0, 7.0), (2.0, 3.0)) == (3.0, 4.0)


def test_vec2_dist():
    assert vec2_dist((1.0, 1.0), (4.0, 5.0)) == pytest.approx(5.0)


def test_lerp_and_vec2_lerp():
    assert lerp(10.0, 20.0, 0.5) == 15.0
    assert vec2_lerp((10.0, 20.0), (20.0, 30.0), 0.1) == (11.0, 21.0)


def test_reflect():
    # Reflection off horizontal surface (normal pointing up: (0, -1))
    v = (3.0, 4.0)
    n = (0.0, -1.0)
    # v' = (3, 4) - 2 * ((3,4).(0,-1)) * (0,-1)
    #    = (3, 4) - 2 * (-4) * (0,-1)
    #    = (3, 4) - (0, 8) = (3, -4)
    assert reflect(v, n) == (3.0, -4.0)


def test_circle_circle_collision():
    # Colliding case
    # Circle A: pos (0, 0), radius 10
    # Circle B: pos (12, 0), radius 5
    # Dist = 12, Sum of radii = 15. Overlap depth = 3. Normal pointing from B to A: (-1, 0)
    colliding, normal, depth = circle_circle_collision((0.0, 0.0), 10.0, (12.0, 0.0), 5.0)
    assert colliding is True
    assert normal[0] == pytest.approx(-1.0)
    assert normal[1] == pytest.approx(0.0)
    assert depth == pytest.approx(3.0)

    # Non-colliding case
    colliding, _, _ = circle_circle_collision((0.0, 0.0), 5.0, (20.0, 0.0), 5.0)
    assert colliding is False


# ==============================================================================
# 2. AI DIFFICULTY PROFILE TESTS
# ==============================================================================

def test_difficulty_profile_creation():
    for level in range(4):
        profile = DifficultyProfile(level)
        assert profile.level == level
        assert profile.max_speed > 0
        assert profile.reaction_delay >= 0
        assert profile.error_mag >= 0


def test_adaptive_difficulty_scaling():
    # Adaptive profile
    profile = DifficultyProfile(3)
    initial_speed = profile.max_speed
    initial_error = profile.error_mag

    # AI is winning significantly -> slow down AI (soften difficulty)
    profile.adapt(ai_score=5, player_score=2)
    assert profile.max_speed < initial_speed
    assert profile.error_mag > initial_error

    # AI is losing significantly -> speed up AI (harden difficulty)
    profile.adapt(ai_score=1, player_score=6)
    # Should adapt back and scale up
    assert profile.max_speed > 5.0


# ==============================================================================
# 3. MOTION SMOOTHER TESTS
# ==============================================================================

def test_motion_smoother():
    smoother = MotionSmoother()
    
    # Feeding initial position
    p1 = smoother.update((0.5, 0.5))
    assert p1 == (0.5, 0.5)
    assert smoother.velocity == (0.0, 0.0)

    # Simulating movement
    # Using a deterministic delay to verify velocity calculation
    # We feed another coordinate and check if velocity is calculated
    time.sleep(0.02)
    p2 = smoother.update((0.6, 0.6))
    
    # Value should be updated
    assert p2[0] > 0.5
    assert p2[1] > 0.5
    
    # Velocity must have non-zero estimation
    assert smoother.velocity != (0.0, 0.0)

    # Test prediction
    pred = smoother.predict(dt=0.016)
    assert pred is not None
    assert 0.0 <= pred[0] <= 1.0
    assert 0.0 <= pred[1] <= 1.0

    # Test reset
    smoother.reset()
    assert smoother.velocity == (0.0, 0.0)
    assert smoother._smoothed is None


# ==============================================================================
# 4. REPLAY RECORDER TESTS
# ==============================================================================

def test_replay_recorder():
    # Recorder with max 10 frames limit (fps=60, max_seconds=10/60)
    recorder = ReplayRecorder(max_seconds=10/60, fps=60)
    
    puck = Puck()
    p1 = Paddle(1, (0, 220, 255))
    p2 = Paddle(2, (255, 0, 200))
    
    # Record 15 frames -> should clamp to circular buffer max length (10)
    for i in range(15):
        puck.x = float(i)
        recorder.record(puck, p1, p2, p1_score=2, p2_score=1, timestamp=i * 0.016)
        
    frames = recorder.get_replay()
    assert len(frames) == 10
    # First cached frame index should represent frame 5 (due to circular shift)
    assert frames[0].puck_x == 5.0
    assert frames[-1].puck_x == 14.0

    # Test pause and clear
    recorder.pause()
    puck.x = 999.0
    recorder.record(puck, p1, p2, p1_score=2, p2_score=1, timestamp=15 * 0.016)
    # Should not record while paused
    assert recorder.get_replay()[-1].puck_x == 14.0

    recorder.clear()
    assert len(recorder.get_replay()) == 0


# ==============================================================================
# 5. PHYSICS & COLLISION SYSTEM TESTS
# ==============================================================================

def test_wall_collisions():
    collision_sys = CollisionSystem()
    puck = Puck()
    puck.radius = 10
    
    # Place puck heading straight at top wall (y=TABLE_TOP, which is 80)
    puck.x = float(TABLE_CENTER_X)
    puck.y = float(TABLE_TOP + 5)
    puck.vx = 0.0
    puck.vy = -10.0 # moving upward
    
    # Trigger collision update (runs substepping)
    side = collision_sys._check_walls(puck)
    
    assert side == 'top'
    # Puck must be repositioned inside boundaries
    assert puck.y >= TABLE_TOP + puck.radius
    # Velocity must be reflected and dampened
    assert puck.vy > 0.0
