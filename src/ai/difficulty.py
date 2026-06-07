"""
Air Hockey Vision - AI Difficulty Configuration
Defines parameters for each AI difficulty level.
"""

from src.core.settings import (
    AI_DIFFICULTY_EASY, AI_DIFFICULTY_MEDIUM,
    AI_DIFFICULTY_HARD, AI_DIFFICULTY_ADAPTIVE,
    AI_SPEEDS, AI_REACTION_DELAYS, AI_ERROR_MAGNITUDES,
)


class DifficultyProfile:
    """Encapsulates all tunable parameters for one difficulty level."""

    def __init__(self, level: int):
        self.level          = level
        self.max_speed      = AI_SPEEDS[level]
        self.reaction_delay = AI_REACTION_DELAYS[level]
        self.error_mag      = AI_ERROR_MAGNITUDES[level]

        # Extra behaviour flags
        if level == AI_DIFFICULTY_EASY:
            self.can_attack          = False
            self.defense_bias        = 0.85
            self.predict_steps       = 10
            self.shoot_chance        = 0.10
            self.defense_track_alpha = 0.06   # sluggish — easy to fool
        elif level == AI_DIFFICULTY_MEDIUM:
            self.can_attack          = True
            self.defense_bias        = 0.60
            self.predict_steps       = 25
            self.shoot_chance        = 0.35
            self.defense_track_alpha = 0.15   # moderate tracking
        elif level == AI_DIFFICULTY_HARD:
            self.can_attack          = True
            self.defense_bias        = 0.30
            self.predict_steps       = 55
            self.shoot_chance        = 0.75
            self.defense_track_alpha = 0.35   # sharp, responsive tracking
        else:  # Adaptive
            self.can_attack          = True
            self.defense_bias        = 0.50
            self.predict_steps       = 35
            self.shoot_chance        = 0.50
            self.defense_track_alpha = 0.22   # balanced tracking

    def adapt(self, ai_score: int, player_score: int):
        """
        Adaptive difficulty: soften when AI dominates, harden when losing.
        """
        if self.level != AI_DIFFICULTY_ADAPTIVE:
            return
        diff = ai_score - player_score
        # If AI winning by ≥2 goals → slow down slightly
        if diff >= 2:
            self.max_speed   = max(5.0, self.max_speed - 0.5)
            self.error_mag   = min(40, self.error_mag + 5)
        elif diff <= -2:
            self.max_speed   = min(12.0, self.max_speed + 0.5)
            self.error_mag   = max(5,   self.error_mag - 5)
