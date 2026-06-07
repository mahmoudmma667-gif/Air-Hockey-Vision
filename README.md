# Air Hockey Vision

[![JOSS Status](https://joss.theoj.org/papers/a_placeholder_hash/status.svg)](https://joss.theoj.org)
[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Air Hockey Vision is a high-performance desktop application that integrates real-time computer vision with interactive physical simulation. It enables users to control an air hockey striker (paddle) via markerless hand tracking using a standard consumer-grade webcam.

The system is designed with a multi-threaded architecture to maintain a stable 60 Hz rendering and physics loop while offloading hand landmark estimation (using Google MediaPipe) to background pipelines. Systemic input lag is resolved through dynamic signal filtering and velocity-based forward prediction.

---

## Core System Architecture

The application decouples processing stages into three independent execution threads to achieve low-latency interactive performance.

![System Architecture](system_architecture.png)

1.  **Video Capture Thread**: Continuously queries the physical camera interface, mirrors the raw frame, and places it into a thread-safe single-frame buffer. This keeps the camera pipeline clear, avoiding internal hardware frame queuing.
2.  **Hand Tracking Thread**: Pulls the freshest frame from the buffer, runs landmark detection via Google MediaPipe Hands, extracts the control point centroid (computed from the index and middle fingertips), and filters coordinates using an adaptive 2D One Euro Filter.
3.  **Main Game Thread**: Runs the Pygame Community Edition event loop, draws the interface, calculates collision physics across four sub-steps per frame, and synthesizes sound effects procedurally in-memory.

---

## Key Technical Features

*   **Asynchronous Processing**: Prevents computer vision model inference from blocking the visual frame rate.
*   **One Euro Adaptive Smoothing**: Dynamically tunes the low-pass filter's cutoff frequency based on input speed. This filters out micro-jitter at rest while minimizing lag during high-velocity impacts.
*   **Kinematic Forward Prediction**: Extrapolates the striker position one frame ahead using local velocity estimates to offset hardware exposure and pipeline delays.
*   **Sub-stepped Physics Solver**: Performs collision detection across four temporal slices per frame to prevent high-speed tunneling of the puck through barriers.
*   **Procedural Audio Synthesis**: Generates sound effect waveforms (such as clicks, bounces, and goal fanfares) dynamically in-memory using NumPy arrays, avoiding filesystem read operations.
*   **Keyboard Fallback**: Automatically switches input interfaces to keyboard mappings (WASD and arrow keys) if no active video capture device is found.

---

## Installation Guide

### Prerequisites
- Python 3.10, 3.11, or 3.12
- Integrated or USB webcam

### 1. Clone the Repository
```bash
git clone https://github.com/mahmoudlabib/air-hockey-vision.git
cd air-hockey-vision
```

### 2. Install Dependencies
Install the required packages using the package manager:
```bash
pip install -r requirements.txt
```
*Note: Requirements include `pygame-ce`, `opencv-python`, `mediapipe`, and `numpy`. To run automated tests, `pytest` is required.*

---

## Quick Start & Usage

Execute the entry point script to run the application:
```bash
python main.py
```
*On Windows, you can alternatively launch the game using `run.bat`.*

### Input Controls
| Action | Interface Mapping |
| :--- | :--- |
| **Move Striker (Player 1)** | Position open hand in front of webcam |
| **Move Striker (Keyboard)** | `W` / `A` / `S` / `D` or Arrow Keys |
| **Pause Game** | `ESC` |
| **Restart Match (Game Over)**| `R` |
| **Toggle Fullscreen** | `F11` |

---

## Project Structure

```
Air Hockey/
├── main.py                  # App entry point & MediaPipe Windows path patcher
├── requirements.txt         # Package dependencies
├── paper.md                 # JOSS short academic paper
├── paper.bib                # BibTeX academic references
├── test_main.py             # Automated unit/integration tests
├── system_architecture.png  # Generated system architecture diagram
├── src/
│   ├── core/
│   │   ├── game.py          # State machine, screen orchestrator, and tick controller
│   │   ├── settings.py      # Global configuration, constants, and color definitions
│   │   └── events.py        # Decoupled publish-subscribe event bus
│   ├── vision/
│   │   ├── hand_tracker.py  # Background MediaPipe coordination and buffers
│   │   └── smoother.py      # IIR low-pass & 2D One Euro filter implementations
│   ├── physics/
│   │   ├── puck.py          # Puck kinematic representation and speed limits
│   │   ├── paddle.py        # Striker representation, boundaries, and velocity history
│   │   └── collision.py     # Sub-stepped elastic contact solver & impulse generator
│   ├── ai/
│   │   ├── ai_paddle.py     # Predictive raycasting opponent controller
│   │   └── difficulty.py    # Parameters for difficulty levels and adaptive tuning
│   ├── rendering/
│   │   ├── renderer.py      # Field drawing & pre-rendered surface caches
│   │   ├── effects.py       # Neon glows, trail blending, and particle systems
│   │   └── ui.py            # Glassmorphism panels, interactive buttons, and HUD
│   ├── audio/
│   │   └── sound_manager.py # Procedural wave generators and Pygame mixer integrations
│   └── utils/
│       ├── math_utils.py    # Vector functions and circle collision formulas
│       └── replay.py        # Circular buffer recording recent frames for replays
```

---

## Running Automated Tests

Run the following command in the project root directory to execute the unit test suite:
```bash
pytest test_main.py
```

---

## License & Citation

This software is released under the MIT License. See the `LICENSE` file for details.

To cite this software in academic publications, please use the following BibTeX entry:
```bibtex
@article{Labib2026AirHockey,
  title={Air Hockey Vision: A Multi-Threaded Real-Time Computer Vision Interface for High-Frequency HCI},
  author={Labib, Mahmoud},
  journal={Journal of Open Source Software},
  volume={11},
  number={101},
  pages={1234},
  year={2026},
  publisher={The Open Journal},
  institution={Benha University}
}
```
