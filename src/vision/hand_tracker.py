"""
Air Hockey Vision - Hand Tracker (High-Performance)
===================================================
An optimized real-time computer vision subsystem that performs hand tracking 
using Google MediaPipe Hands inside a dedicated background thread. 

Key Architectural and Algorithmic Features:
-------------------------------------------
1. Dedicated Camera Drain Thread:
   Drains the hardware buffer of the OpenCV VideoCapture device as fast as the
   sensor permits (camera frame rates >= 30 FPS) to prevent internal buffer 
   queuing, minimizing processing-to-display frame latency.

2. MediaPipe Hand Landmark Processing Thread:
   Processes the frames at a capped rate (HAND_PROCESS_FPS) using model complexity 0 
   (lightweight model) to keep CPU utilisation low while maintaining high accuracy.

3. Triple-Buffering Frame Pipeline:
   Protects shared frame resources across threads using mutex locks, ensuring that 
   the processing thread always receives the freshest raw camera frame.

4. Precise Human-Computer Interaction (HCI) Control Point:
   Computes the centroid of the index fingertip (landmark 8) and middle fingertip 
   (landmark 12). This control point is chosen over the wrist or palm centre as it 
   provides the most intuitive, stable, and reactive control for air hockey paddles, 
   mimicking a real hand-held striker.

5. Motion Smoothing and Prediction:
   Applies a 2D One Euro Filter via the MotionSmoother module. The velocity is 
   dynamically estimated and used for frame-to-frame extrapolation, compensating 
   for the display pipeline and sensor delay.
"""

import threading
import time
import math
import cv2
import numpy as np

from src.core.settings import (
    CAMERA_WIDTH, CAMERA_HEIGHT,
    CAMERA_FPS, HAND_PROCESS_FPS,
    TRACKING_CONFIDENCE, DETECTION_CONFIDENCE,
    HAND_SMOOTHING_ALPHA,
    CAM_PANEL_W, CAM_PANEL_H,
)
from src.vision.smoother import MotionSmoother

# MediaPipe hand-connection skeleton for overlay drawing
_MP_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),          # thumb
    (0,5),(5,6),(6,7),(7,8),          # index
    (0,9),(9,10),(10,11),(11,12),     # middle
    (0,13),(13,14),(14,15),(15,16),   # ring
    (0,17),(17,18),(18,19),(19,20),   # pinky
    (5,9),(9,13),(13,17),             # palm
]


class HandTracker:
    """
    Coordinates multi-threaded video acquisition and hand landmark detection.
    
    Attributes:
        MAX_HANDS (int): Maximum number of hands to track simultaneously (default: 2).
    """
    MAX_HANDS = 2

    # --- Landmark control indices ---
    # Centroid of Index Fingertip (8) + Middle Fingertip (12) provides the control point.
    # Wrist landmark (0) is monitored for stability and geometry estimations.
    _CTRL_A = 8    # Index fingertip
    _CTRL_B = 12   # Middle fingertip
    _CTRL_C = 0    # Wrist anchor

    def __init__(self):
        self._mp_hands = None
        self._hands    = None
        self._cap      = None
        self._cam_thread: threading.Thread | None = None
        self._thread: threading.Thread | None = None
        self._lock     = threading.Lock()
        self._running  = False
        self._process_interval = 1.0 / max(1, HAND_PROCESS_FPS)
        self._last_process_time = 0.0
        self._lost_grace = 0.05

        self._smoothers: list[MotionSmoother] = [
            MotionSmoother(alpha=HAND_SMOOTHING_ALPHA) for _ in range(self.MAX_HANDS)
        ]

        self.tracking_quality: list[float] = [0.0, 0.0]
        self.is_tracking: list[bool]       = [False, False]
        self.is_open: list[bool]           = [False, False]

        # Smoothed normalized positions
        self._positions: dict[int, tuple]  = {}
        self._hand_labels: dict[int, str]  = {}
        self._last_seen: list[float]        = [0.0, 0.0]

        # Raw landmarks (list of (x_px, y_px) on the camera frame)
        self.raw_landmarks: dict[int, list] = {}

        # ── Triple-buffer: always the freshest camera frame ────────────────
        self._frame_lock  = threading.Lock()
        self._raw_frame: np.ndarray | None = None
        self._raw_frame_id = 0
        self._processed_frame_id = -1
        self._frame_ready = threading.Event()

        self.latest_frame: np.ndarray | None = None
        self.thumbnail_rgb_bytes: bytes | None = None
        self.camera_available = False

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self, camera_index: int = 0) -> bool:
        try:
            import mediapipe as mp
            self._mp_hands = mp.solutions.hands
        except Exception as e:
            print(f"[Vision] MediaPipe import failed: {e}")
            return False

        # Open camera — prefer DirectShow on Windows for lower latency
        self._cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        if not self._cap.isOpened():
            self._cap = cv2.VideoCapture(camera_index)
        if not self._cap.isOpened():
            print(f"[Vision] Failed to open camera {camera_index}")
            self.camera_available = False
            return False

        # Camera settings for minimum latency
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAMERA_WIDTH)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        self._cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)   # 1-frame buffer = always fresh

        # Try to disable any camera-internal processing that adds latency
        try:
            self._cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
        except Exception:
            pass

        # MediaPipe: complexity 0 = fastest model, still very accurate
        try:
            self._hands = self._mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=self.MAX_HANDS,
                min_detection_confidence=DETECTION_CONFIDENCE,
                min_tracking_confidence=TRACKING_CONFIDENCE,
                model_complexity=0,
            )
        except Exception as e:
            print(f"[Vision] MediaPipe Hands init failed: {e}")
            self._hands = None

        self.camera_available = True
        self._running = True
        self._last_process_time = 0.0
        self._processed_frame_id = -1
        self._last_seen = [0.0, 0.0]

        # Thread 1: drains camera buffer as fast as possible
        self._cam_thread = threading.Thread(
            target=self._camera_worker, daemon=True, name="CamDrain"
        )
        self._cam_thread.start()

        # Thread 2: processes the latest frame through MediaPipe
        self._thread = threading.Thread(
            target=self._worker, daemon=True, name="MPProcess"
        )
        self._thread.start()

        return True

    def stop(self):
        self._running = False
        self._frame_ready.set()   # unblock processing thread
        if hasattr(self, '_cam_thread') and self._cam_thread:
            self._cam_thread.join(timeout=1.0)
        if self._thread:
            self._thread.join(timeout=1.0)
        if self._cap:
            self._cap.release()
        if self._hands:
            self._hands.close()

    def get_position(self, hand_index: int = 0) -> tuple | None:
        """
        Retrieves the filtered, normalized coordinates (x, y) of the requested hand.
        
        Args:
            hand_index (int): Index of the tracked hand (0 for primary, 1 for secondary).
            
        Returns:
            tuple[float, float] | None: Normalized (x, y) coordinates in [0, 1] range, 
                                        where (0,0) is top-left and (1,1) is bottom-right,
                                        or None if tracking is currently lost.
        """
        with self._lock:
            return self._positions.get(hand_index)

    def get_predicted_position(self, hand_index: int = 0,
                                lookahead: float = 0.016) -> tuple | None:
        """
        Calculates a velocity-predicted position `lookahead` seconds into the future.
        
        This compensates for end-to-end processing delays (sensor capture, MediaPipe 
        graph inference, OS window scheduling, and display refresh).
        
        Args:
            hand_index (int): Index of the tracked hand.
            lookahead (float): Extrapolation interval in seconds (default is ~1 frame at 60Hz: 0.016s).
            
        Returns:
            tuple[float, float] | None: Predicted normalized (x, y) coordinates, 
                                        or None if tracking is lost.
        """
        with self._lock:
            pos = self._positions.get(hand_index)
            if pos is None:
                return None
        pred = self._smoothers[hand_index].predict(dt=lookahead)
        return pred if pred is not None else pos

    def get_hand_label(self, hand_index: int = 0) -> str:
        with self._lock:
            return self._hand_labels.get(hand_index, "?")

    def get_landmarks_px(self, hand_index: int = 0) -> list | None:
        with self._lock:
            return self.raw_landmarks.get(hand_index)

    def get_preview_snapshot(self):
        """Return the latest preview frame plus a small copy of landmark data."""
        with self._lock:
            return self.latest_frame, {
                idx: list(points) for idx, points in self.raw_landmarks.items()
            }

    def get_thumbnail_bytes(self) -> bytes | None:
        with self._lock:
            return self.thumbnail_rgb_bytes

    def set_smoothing(self, smoothness: float):
        for smoother in self._smoothers:
            smoother.configure(smoothness)

    # ── Background workers ────────────────────────────────────────────────────

    def _camera_worker(self):
        """
        Runs at camera speed (≥30 fps).  Continuously reads frames and stores
        only the latest one so the processing thread never gets stale data.
        """
        while self._running:
            ret, frame = self._cap.read()
            if ret:
                # Mirror immediately — eliminates confusion between left/right
                frame = cv2.flip(frame, 1)
                with self._frame_lock:
                    self._raw_frame = frame
                    self._raw_frame_id += 1
                self._frame_ready.set()
            else:
                time.sleep(0.005)

    def _worker(self):
        """
        Processes the absolute freshest frame through MediaPipe.
        Skips frames if processing is too slow (always uses latest).
        """
        while self._running:
            # Block until a new frame arrives (or timeout after 100 ms)
            self._frame_ready.wait(timeout=0.1)
            self._frame_ready.clear()

            now = time.perf_counter()
            wait_left = self._process_interval - (now - self._last_process_time)
            if wait_left > 0:
                time.sleep(wait_left)
                if not self._running:
                    break
            self._last_process_time = time.perf_counter()

            with self._frame_lock:
                frame = self._raw_frame
                frame_id = self._raw_frame_id

            if frame is None or frame_id == self._processed_frame_id:
                continue
            self._processed_frame_id = frame_id

            new_positions: dict[int, tuple] = {}
            new_labels:    dict[int, str]   = {}
            new_tracking:  list[bool]       = [False, False]
            new_open:      list[bool]       = [False, False]
            new_landmarks: dict[int, list]  = {}

            if self._hands is not None:
                self._process_mediapipe_results(
                    frame, new_positions, new_labels, new_tracking, new_open, new_landmarks
                )

            with self._lock:
                prev_positions = dict(self._positions)
                prev_labels = dict(self._hand_labels)
                prev_open = list(self.is_open)
                prev_landmarks = dict(self.raw_landmarks)

            self._handle_tracking_dropouts(
                new_positions, new_labels, new_tracking, new_open, new_landmarks,
                prev_positions, prev_labels, prev_open, prev_landmarks
            )

            thumb_bytes = self._render_thumbnail(frame, new_landmarks)

            with self._lock:
                self._positions   = new_positions
                self._hand_labels = new_labels
                self.is_tracking  = new_tracking
                self.is_open      = new_open
                self.raw_landmarks= new_landmarks
                self.latest_frame = frame
                self.thumbnail_rgb_bytes = thumb_bytes

    def _process_mediapipe_results(self, frame, new_positions, new_labels, new_tracking, new_open, new_landmarks):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self._hands.process(rgb)
        rgb.flags.writeable = True

        h, w = frame.shape[:2]

        if not results.multi_hand_landmarks:
            return

        for i, (hand_lms, hand_info) in enumerate(zip(results.multi_hand_landmarks, results.multi_handedness)):
            if i >= self.MAX_HANDS:
                break

            lm = hand_lms.landmark
            raw_x = (lm[self._CTRL_A].x + lm[self._CTRL_B].x) / 2.0
            raw_y = (lm[self._CTRL_A].y + lm[self._CTRL_B].y) / 2.0
            smoothed = self._smoothers[i].update((raw_x, raw_y))

            new_positions[i] = smoothed
            new_labels[i]    = hand_info.classification[0].label
            new_tracking[i]  = True
            self._last_seen[i] = self._last_process_time
            self.tracking_quality[i] = self._smoothers[i].quality

            wrist = lm[0]
            tips = [8, 12, 16, 20]
            mcps = [5,  9, 13, 17]
            open_fingers = sum(
                1 for t, m in zip(tips, mcps)
                if math.hypot(lm[t].x - wrist.x, lm[t].y - wrist.y) > math.hypot(lm[m].x - wrist.x, lm[m].y - wrist.y)
            )
            new_open[i] = (open_fingers >= 2)

            new_landmarks[i] = [(int(lm_pt.x * w), int(lm_pt.y * h)) for lm_pt in lm]

    def _handle_tracking_dropouts(self, new_positions, new_labels, new_tracking, new_open, new_landmarks,
                                  prev_positions, prev_labels, prev_open, prev_landmarks):
        for i in range(self.MAX_HANDS):
            if not new_tracking[i]:
                recently_seen = (self._last_process_time - self._last_seen[i] <= self._lost_grace)
                if recently_seen and i in prev_positions:
                    dt = self._last_process_time - self._last_seen[i]
                    pred = self._smoothers[i].predict(dt=dt)
                    new_positions[i] = pred if pred is not None else prev_positions[i]
                    new_labels[i] = prev_labels.get(i, "?")
                    new_tracking[i] = True
                    new_open[i] = prev_open[i]
                    if i in prev_landmarks:
                        new_landmarks[i] = prev_landmarks[i]
                    self.tracking_quality[i] = max(0.0, self.tracking_quality[i] * 0.75)
                else:
                    self._smoothers[i].reset()
                    self.tracking_quality[i] = 0.0
                    new_open[i] = False

    def _render_thumbnail(self, frame, new_landmarks) -> bytes | None:
        if frame is None:
            return None
        tw, th = CAM_PANEL_W, CAM_PANEL_H
        try:
            small = cv2.resize(frame, (tw, th))
            h_orig, w_orig = frame.shape[:2]
            sx, sy = tw / w_orig, th / h_orig
            
            for i in range(self.MAX_HANDS):
                if i in new_landmarks:
                    color_bgr = (220, 130, 40) if i == 0 else (40, 120, 220)
                    lms = new_landmarks[i]
                    for (a, b) in _MP_CONNECTIONS:
                        ax, ay = int(lms[a][0] * sx), int(lms[a][1] * sy)
                        bx, by = int(lms[b][0] * sx), int(lms[b][1] * sy)
                        cv2.line(small, (ax, ay), (bx, by), color_bgr, 1)
                    for pt in lms:
                        px, py = int(pt[0] * sx), int(pt[1] * sy)
                        cv2.circle(small, (px, py), 2, (255, 255, 255), -1)
            rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
            return rgb.tobytes()
        except Exception:
            return None
