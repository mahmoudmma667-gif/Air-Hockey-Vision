import pygame
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.display.set_mode((1280, 720))

from src.core.settings import *
from src.rendering.ui import ScoreDisplay
from src.rendering.effects import ParticleSystem
from src.screens.game_screen import GameScreen

surface = pygame.Surface((1280, 720))
surface.fill(C_BACKGROUND)

# Draw score bar
score_disp = ScoreDisplay()
score_disp.flash_p1()
score_disp.update()
score_disp.draw(surface, 1, 0, 180, MODE_VS_AI)

# Draw Goal Banner
cx, cy = TABLE_CENTER_X, TABLE_CENTER_Y
color = C_GOAL_GLOW_P1
scorer = "PLAYER 1"
bw, bh = 460, 112
ban = pygame.Surface((bw, bh), pygame.SRCALPHA)
ban.fill((0, 0, 0, 175))
bx = cx - bw // 2
by = cy - 60
surface.blit(ban, (bx, by))
pygame.draw.rect(surface, color, (bx, by, bw, bh), 2, border_radius=8)

glow_c = (*color[:3], 60)
inner_s = pygame.Surface((bw - 4, bh - 4), pygame.SRCALPHA)
pygame.draw.rect(inner_s, glow_c, inner_s.get_rect(), 4, border_radius=6)
surface.blit(inner_s, (bx + 2, by + 2))

from src.rendering.ui import render_text, FontCache
render_text(surface, "GOAL!", FontCache.get(FONT_LARGE, bold=True), color, (cx, by + 42), shadow=True)
render_text(surface, f"{scorer} SCORES", FontCache.get(FONT_SMALL), color, (cx, by + bh - 26))

pygame.image.save(surface, "goal_test.png")
print("Saved goal_test.png")
