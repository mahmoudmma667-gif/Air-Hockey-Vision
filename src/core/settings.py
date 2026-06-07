"""
Air Hockey Vision - Settings & Constants
Global configuration for the entire game.
"""

# ─── Window ──────────────────────────────────────────────────────────────────
WINDOW_WIDTH  = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE  = "Air Hockey Vision"
TARGET_FPS    = 60
MAX_FRAME_DT  = 1.0 / 30.0  # Clamp big frame spikes so brief stalls do not jerk motion

# ─── Camera panels (sides) ───────────────────────────────────────────────────
CAM_PANEL_W   = 180    # width of each side camera panel
CAM_PANEL_H   = 135    # camera thumbnail height

# ─── Table / Field ───────────────────────────────────────────────────────────
TABLE_MARGIN_X = 40
TABLE_MARGIN_Y = 80
TABLE_LEFT     = TABLE_MARGIN_X
TABLE_TOP      = TABLE_MARGIN_Y
TABLE_RIGHT    = WINDOW_WIDTH  - TABLE_MARGIN_X
TABLE_BOTTOM   = WINDOW_HEIGHT - 20
TABLE_WIDTH    = TABLE_RIGHT  - TABLE_LEFT
TABLE_HEIGHT   = TABLE_BOTTOM - TABLE_TOP
TABLE_CENTER_X = (TABLE_LEFT + TABLE_RIGHT)  // 2
TABLE_CENTER_Y = (TABLE_TOP  + TABLE_BOTTOM) // 2

# Score bar (top)
SCORE_BAR_TOP    = 0
SCORE_BAR_HEIGHT = TABLE_MARGIN_Y

# Goal settings (now on left and right, so this is goal height)
GOAL_SIZE   = 240
GOAL_HALF   = GOAL_SIZE // 2

# ─── Physics ─────────────────────────────────────────────────────────────────
PUCK_RADIUS         = 18
PADDLE_RADIUS       = 34
PUCK_FRICTION       = 0.999
PUCK_MAX_SPEED      = 18.0
PUCK_MIN_SPEED      = 0.05
PUCK_RESTITUTION    = 0.88
PHYSICS_SUBSTEPS    = 4

# ─── AI ──────────────────────────────────────────────────────────────────────
AI_DIFFICULTY_EASY    = 0
AI_DIFFICULTY_MEDIUM  = 1
AI_DIFFICULTY_HARD    = 2
AI_DIFFICULTY_ADAPTIVE= 3

AI_SPEEDS = {
    AI_DIFFICULTY_EASY:     4.5,
    AI_DIFFICULTY_MEDIUM:   7.0,
    AI_DIFFICULTY_HARD:     11.0,
    AI_DIFFICULTY_ADAPTIVE: 9.0,
}
AI_REACTION_DELAYS = {
    AI_DIFFICULTY_EASY:     0.25,
    AI_DIFFICULTY_MEDIUM:   0.12,
    AI_DIFFICULTY_HARD:     0.04,
    AI_DIFFICULTY_ADAPTIVE: 0.08,
}
AI_ERROR_MAGNITUDES = {
    AI_DIFFICULTY_EASY:     55,
    AI_DIFFICULTY_MEDIUM:   25,
    AI_DIFFICULTY_HARD:     8,
    AI_DIFFICULTY_ADAPTIVE: 18,
}

# ─── Scoring ─────────────────────────────────────────────────────────────────
SCORE_TO_WIN    = 7
MATCH_DURATION  = 0           # 0 = unlimited

# ─── Vision / Tracking ───────────────────────────────────────────────────────
CAMERA_INDEX          = 0
CAMERA_WIDTH          = 640
CAMERA_HEIGHT         = 480
CAMERA_FPS            = 30    # 30fps is steadier on common webcams than requested 60fps
HAND_PROCESS_FPS      = 30    # MediaPipe cap; extra frames are dropped for lower CPU load
CAMERA_PREVIEW_FPS    = 15    # Thumbnail refresh cap; tracking still runs at HAND_PROCESS_FPS
HAND_SMOOTHING_ALPHA  = 0.95   # Kept for API compat; One Euro Filter is used instead
TRACKING_CONFIDENCE   = 0.6    # Higher = more stable, fewer flickering losses
DETECTION_CONFIDENCE  = 0.65  # Higher = fewer false hand detections

# ─── Colors ───────────────────────────────────────────────────────────────────

# Field (futuristic dark style)
C_BACKGROUND    = (5, 5, 10)
C_FIELD_LIGHT   = (15, 18, 30)     # dark blue-grey grid/stripe
C_FIELD_DARK    = (10, 12, 22)     # darker blue-grey
C_FIELD_LINE    = (40, 60, 120)    # glowing blue lines
C_FIELD_NET     = (60, 80, 140)

# Score bar
C_SCORE_BAR     = (8,  8,  12)
C_SCORE_BAR2    = (15, 15, 22)

# Paddles (Neon Cyan and Magenta)
C_PADDLE_P1     = (0, 220, 255)    # Cyan (Player 1 / left)
C_PADDLE_P2     = (255, 0, 200)    # Magenta (Player 2 / AI / right)
C_PADDLE_AI     = (255, 0, 200)    # same as P2

# Puck
C_PUCK          = (240, 255, 255)
C_PUCK_SHADOW   = (20, 40, 80)

# Goals
C_GOAL_GLOW_P1  = (0, 220, 255)    # Cyan goal glow (left)
C_GOAL_GLOW_P2  = (255, 0, 200)    # Magenta goal glow (right)

# UI / Misc
C_WHITE         = (255, 255, 255)
C_UI_TEXT       = (230, 230, 255)
C_UI_DIM        = (120, 120, 150)
C_UI_ACCENT     = (80,  160, 255)
C_NEON_CYAN     = (0,   220, 255)
C_NEON_MAGENTA  = (255,   0, 200)
C_NEON_YELLOW   = (255, 220,   0)
C_NEON_GREEN    = (0,   255, 120)
C_NEON_ORANGE   = (255, 140,   0)
C_NEON_PURPLE   = (160,   0, 255)
C_DARK_BLUE     = (10,   20,  60)

# Particles
C_PARTICLE_GOAL = [(255,220,0),(255,100,0),(255,50,120),(80,160,255),(255,255,255)]

# Trails
TRAIL_LENGTH       = 16
TRAIL_FADE_FACTOR  = 0.80

# Particles
GOAL_PARTICLE_COUNT = 130

# ─── Game States ─────────────────────────────────────────────────────────────
STATE_MAIN_MENU  = "main_menu"
STATE_GAME       = "game"
STATE_SETTINGS   = "settings"
STATE_STATS      = "stats"
STATE_PAUSE      = "pause"
STATE_GOAL       = "goal"
STATE_GAME_OVER  = "game_over"

# ─── Game Modes ──────────────────────────────────────────────────────────────
MODE_VS_AI       = "vs_ai"
MODE_TWO_PLAYER  = "two_player"
MODE_TRAINING    = "training"
MODE_CHALLENGE   = "challenge"

# ─── Themes ──────────────────────────────────────────────────────────────────
THEME_NEON       = "neon"
THEME_SOCCER     = "soccer"
THEMES           = [THEME_NEON, THEME_SOCCER]

# ─── Settings Defaults ───────────────────────────────────────────────────────
SENSITIVITY      = 0.6

# ─── Font sizes ──────────────────────────────────────────────────────────────
FONT_HUGE   = 88
FONT_LARGE  = 52
FONT_MEDIUM = 30
FONT_SMALL  = 20
FONT_TINY   = 15
