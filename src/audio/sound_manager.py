r"""
Air Hockey Vision - Procedural Sound Manager
============================================
Synthesizes all audio effects programmatically using NumPy and Pygame mixer.
This eliminates external dependencies and reduces asset footprint to zero.

Procedural Synthesis Models:
----------------------------
1. Physical Impact Click (Puck/Paddle & Puck/Wall hits):
   Impacts are synthesized by combining a decaying fundamental sine tone with 
   Gaussian white noise to model structural vibrations:
     y(t) = (0.7 * sin(2 * \pi * f * t) + 0.3 * N(t)) * e^{-\lambda * t}
   where N(t) is standard normal Gaussian noise, f is the impact frequency 
   (220 Hz for walls, 440 Hz for paddles), and \lambda is the decay rate.

2. Goal Fanfare (Segmented Arpeggio):
   Goal celebrations are procedural arpeggios (C4 -> E4 -> G4 -> C5). 
   The duration is divided into four equal segments, each containing a sine wave
   at the corresponding note frequency modulated by a local exponential envelope:
     y_seg(t) = sin(2 * \pi * f_note * t) * e^{-3 * t}

3. Game Over Fanfare (Two-Tone Decrescendo):
   Synthesizes a descending two-tone interval (392 Hz -> 261 Hz) using two 
   successive waves with separate exponential decay envelopes.
"""

import numpy as np
import pygame
import math


class SoundManager:
    """
    Procedurally synthesizes and coordinates game sound effects.
    
    Attributes:
        SAMPLE_RATE (int): Audio sampling frequency (default: 44100 Hz).
        CHANNELS (int): Stereo channels (default: 2).
        BIT_DEPTH (int): Signed 16-bit encoding (default: -16).
    """

    SAMPLE_RATE = 44100
    CHANNELS    = 2
    BIT_DEPTH   = -16    # signed 16-bit

    def __init__(self):
        self.enabled = True
        self.volume  = 0.7
        self._sounds: dict[str, pygame.sndarray.make_sound] = {}
        self._music_channel: pygame.Channel | None = None

    def init(self):
        """Initialize mixer and pre-generate sounds."""
        try:
            pygame.mixer.pre_init(
                self.SAMPLE_RATE, self.BIT_DEPTH,
                self.CHANNELS, 512
            )
            pygame.mixer.init()
            pygame.mixer.set_num_channels(16)
            self._generate_sounds()
        except Exception as e:
            print(f"[Audio] Mixer init failed: {e}")
            self.enabled = False

    # ── Public play API ───────────────────────────────────────────────────────

    def play(self, name: str, volume: float = 1.0):
        if not self.enabled:
            return
        snd = self._sounds.get(name)
        if snd:
            snd.set_volume(self.volume * volume)
            snd.play()

    def play_goal(self):
        self.play('goal', 1.0)

    def play_wall_hit(self, intensity: float = 1.0):
        self.play('wall_hit', 0.5 * intensity)

    def play_paddle_hit(self, intensity: float = 1.0):
        self.play('paddle_hit', 0.8 * intensity)

    def play_menu_select(self):
        self.play('menu_select', 0.6)

    def play_menu_hover(self):
        self.play('menu_hover', 0.3)

    def play_countdown(self):
        self.play('countdown', 0.9)

    def play_game_over(self):
        self.play('game_over', 1.0)

    def set_master_volume(self, v: float):
        self.volume = max(0.0, min(1.0, v))

    # ── Sound generation ──────────────────────────────────────────────────────

    def _generate_sounds(self):
        sr = self.SAMPLE_RATE
        self._sounds['wall_hit']    = self._make_impact(sr, freq=220, dur=0.06, decay=8.0)
        self._sounds['paddle_hit']  = self._make_impact(sr, freq=440, dur=0.09, decay=6.0)
        self._sounds['goal']        = self._make_goal_fanfare(sr)
        self._sounds['menu_select'] = self._make_blip(sr, freq=880, dur=0.12)
        self._sounds['menu_hover']  = self._make_blip(sr, freq=660, dur=0.06)
        self._sounds['countdown']   = self._make_blip(sr, freq=1200, dur=0.10)
        self._sounds['game_over']   = self._make_game_over(sr)

    def _to_sound(self, mono: np.ndarray) -> pygame.mixer.Sound:
        stereo = np.column_stack([mono, mono])
        stereo = np.clip(stereo, -32767, 32767).astype(np.int16)
        return pygame.sndarray.make_sound(stereo)

    def _make_impact(self, sr, freq=300, dur=0.08, decay=10.0) -> pygame.mixer.Sound:
        t = np.linspace(0, dur, int(sr * dur), endpoint=False)
        env = np.exp(-decay * t)
        # white noise + sine click
        noise = np.random.randn(len(t)) * 0.3
        tone  = np.sin(2 * np.pi * freq * t)
        wave  = (tone * 0.7 + noise) * env
        wave  = (wave / np.max(np.abs(wave) + 1e-9) * 28000).astype(np.int16)
        return self._to_sound(wave)

    def _make_blip(self, sr, freq=880, dur=0.1) -> pygame.mixer.Sound:
        t    = np.linspace(0, dur, int(sr * dur), endpoint=False)
        env  = np.exp(-6 * t / dur)
        wave = np.sin(2 * np.pi * freq * t) * env
        wave = (wave * 28000).astype(np.int16)
        return self._to_sound(wave)

    def _make_goal_fanfare(self, sr) -> pygame.mixer.Sound:
        dur  = 0.8
        t    = np.linspace(0, dur, int(sr * dur), endpoint=False)
        # Rising arpeggio  C4 E4 G4 C5
        freqs = [261.6, 329.6, 392.0, 523.3]
        seg   = len(t) // len(freqs)
        wave  = np.zeros(len(t))
        for i, f in enumerate(freqs):
            sl = slice(i * seg, (i + 1) * seg)
            tt = t[sl] - t[i * seg]
            env = np.exp(-3 * tt)
            wave[sl] = np.sin(2 * np.pi * f * tt) * env
        wave = (wave / (np.max(np.abs(wave)) + 1e-9) * 30000).astype(np.int16)
        return self._to_sound(wave)

    def _make_game_over(self, sr) -> pygame.mixer.Sound:
        dur = 1.2
        t   = np.linspace(0, dur, int(sr * dur), endpoint=False)
        # Descending two-tone
        mid  = len(t) // 2
        wave = np.zeros(len(t))
        tt0  = t[:mid]
        tt1  = t[mid:] - t[mid]
        env0 = np.exp(-2 * tt0)
        env1 = np.exp(-2 * tt1)
        wave[:mid] = np.sin(2 * np.pi * 392 * tt0) * env0
        wave[mid:] = np.sin(2 * np.pi * 261 * tt1) * env1
        wave = (wave / (np.max(np.abs(wave)) + 1e-9) * 28000).astype(np.int16)
        return self._to_sound(wave)
