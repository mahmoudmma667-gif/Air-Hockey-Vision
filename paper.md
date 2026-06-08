---
title: 'Air Hockey Vision: A Multi-Threaded Real-Time Computer Vision Interface for High-Frequency Human-Computer Interaction'
tags:
  - Python
  - computer vision
  - human-computer interaction
  - real-time tracking
  - game physics
  - signal processing
authors:
  - name: Mahmoud Labib
    orcid: 0009-0003-8176-9216
    affiliation: 1
affiliations:
  - name: Faculty of Specific Education, Benha University, Egypt
    index: 1
date: 7 June 2026
bibliography: paper.bib
---

# Summary

Modern consumer-grade human-computer interaction (HCI) systems increasingly rely on markerless tracking to facilitate natural user inputs. While frameworks like Google MediaPipe Hands [@zhang2020mediapipe] and the general MediaPipe processing pipeline [@lugaresi2019mediapipe] make hand landmark estimation accessible, deploying them in high-frequency interactive applications remains a challenge. Direct integration of vision models into graphical rendering loops introduces severe frame rate degradation and input lag, making fast-paced tasks such as physical simulator control virtually unplayable.

`Air Hockey Vision` addresses this problem by demonstrating a multi-threaded design pattern and signal processing pipeline. Written in Python and leveraging Pygame Community Edition [@pygamece], the software implements a real-time air hockey physical simulation controlled via computer vision. By decoupling camera frame acquisition, landmark detection, and graphical rendering into distinct threads, `Air Hockey Vision` maintains a consistent 60 FPS graphics loop while performing hand tracking in the background. The system integrates a 2D One Euro Filter [@casiez2012euro] to eliminate tracking jitter and applies linear velocity-based forward prediction to compensate for end-to-end hardware latency.

# Statement of Need

In interactive design and HCI pedagogy, students and researchers frequently need functional, low-latency codebases to study input smoothing, predictive kinematics, and physical collision dynamics. Existing webcam games or gesture-controlled interfaces are typically built as monolithic single-threaded applications. In such systems, a single MediaPipe inference call (taking between 15ms and 45ms depending on the hardware) blocks the rendering loop, causing visual stuttering and erratic physics.

`Air Hockey Vision` serves two primary needs in the scientific and educational communities:
1. **Reference Implementation of Low-Latency HCI**: It provides a concrete, high-performance Python implementation of a multi-threaded processing pipeline. It showcases how to implement a triple-buffered frame queue using mutex locks to share frames across a camera-drain thread, a computer vision thread, and a main game thread without thread blockages (see Figure 1).
2. **Pedagogical Laboratory for Signal Filtering & Physics**: It contains modular implementations of advanced algorithms:
    - **One Euro Filter**: Demonstrates adaptive low-pass filtering where the cutoff frequency varies dynamically with signal velocity, resolving the trade-off between jitter at rest and lag during high-speed movement.
    - **Lag Compensation**: Implements kinematic forward-extrapolation to counter pipeline lag.
    - **Sub-stepped Collision Solver**: Demonstrates a sub-stepping technique (temporal discretisation) to prevent collision tunnelling of circles at high speeds.
    - **Procedural Sound Generation**: Shows how mathematical models (sine modulation, Gaussian noise blending, envelopes) can generate game sounds programmatically inside NumPy arrays [@harris2020numpy], bypassing filesystem read lag.

![System Architecture of Air Hockey Vision showing parallel processing loops.](system_architecture.png)

# State of the Field

In the domain of computer vision games and interfaces, popular repositories either focus on simple interactive demos (e.g., CVZone or basic OpenCV [@bradski2000opencv] scripts) that lack physical realism, or utilize heavy engines (like Unity or Unreal) that obscure the low-level signal processing pipelines. Similar frameworks such as Leap Motion SDKs provide excellent low-latency tracking but require specialized, expensive hardware sensors. `Air Hockey Vision` bridges this gap by delivering Leap-Motion-like high-fidelity interactive performance using standard, low-cost webcams, serving as a transparent, open-source template for desktop HCI applications. It builds on standard Pygame [@pygameorig] and Pygame Community Edition [@pygamece] constructs to achieve low rendering overhead.

# Software Design

The software architecture of `Air Hockey Vision` is engineered to resolve the bottlenecks inherent in interpreting vision-based signals within real-time visual loops. The application decouples operations into three asynchronous, concurrent execution threads:

1. **Camera Acquisition Thread (`CamDrain`)**: Continuously queries the physical camera interface using OpenCV [@bradski2000opencv] at the camera's native speed ($\ge 30$ Hz). It automatically mirrors the raw frame and stores the newest frame in a single-frame queue protected by a mutual exclusion lock (`_frame_lock`). This design ensures that the internal operating system buffers are kept clear, eliminating the processing latency caused by accumulated old frames.
2. **Hand Tracking Thread (`MPProcess`)**: Pulls the freshest raw frame from the buffer and runs landmark detection via MediaPipe Hands [@zhang2020mediapipe] using model complexity 0 to minimize computational overhead. Because the MediaPipe C++ inference backend releases Python's Global Interpreter Lock (GIL) during processing, this architecture achieves true parallel execution, preventing CPU contention with the rendering thread. Once coordinates are detected, they are smoothed using the dynamic One Euro Filter and buffered for the main loop.
3. **Main Game Loop**: Integrates the game state machine, user interface, collision physics, and procedural audio synthesis at a stable 60 Hz. The game loop operates independently of the hand tracker's frame rate. When it queries the striker's target position, it applies kinematic forward-extrapolation to compensate for the pipeline delay.

## Thread Safety and Triple Buffering

To share image frames across threads without blocking the rendering or capture threads, the pipeline implements a light triple-buffering logic. When the camera captures a frame, it locks the buffer, writes the frame, updates a tracking ID, and releases the lock. The processing thread checks if a new ID is available; if so, it copies the frame under lock and processes it. This guarantees that the computer vision model always processes the absolute newest physical frame, and the rendering loop never blocks waiting for the model to finish inference.

## Landmark Selection and Control Point Centroid

Rather than tracking the wrist or bounding box center, `Air Hockey Vision` tracks the centroid computed from the index fingertip (landmark 8) and middle fingertip (landmark 12). This control point mimics the natural physical contact point of a hand gripping a physical air hockey mallet, providing superior motor control, stability, and intuitive control dynamics for users.

## One Euro Filter Formulation

The One Euro Filter adapts its cutoff frequency $f_c$ based on the input signal's speed $|dX|$:
$$f_c = f_{min} + \beta \cdot |dX|$$
where $f_{min}$ is the minimum cutoff frequency (set to $1.0$ Hz to filter out static hand jitter) and $\beta$ is the speed coefficient (set to $0.007$ to reduce lag during fast movements). The dynamic cutoff frequency is used to calculate the smoothing parameter $\alpha$:
$$\alpha = \frac{1}{1 + \frac{1}{2 \pi \cdot f_c \cdot dt}}$$
This dynamic adjustment ensures that when the user's hand is stationary, $f_c$ is low, heavily smoothing out camera sensor noise. When the hand moves rapidly, $f_c$ increases, allowing high-frequency coordinates through to minimize tracking lag.

## Lag Compensation via Extrapolation

End-to-end hardware latency is mitigated by kinematic forward prediction. Using the filtered coordinate $P_{smooth}$ and its estimated velocity $V_{smooth}$, the system predicts the hand position at $t + dt$:
$$P_{pred} = P_{smooth} + V_{smooth} \cdot dt$$
where $dt$ represents the estimated end-to-end processing and display latency (configured to $0.016$ seconds or approximately one rendering frame). This extrapolation aligns the virtual paddle with the user's physical hand position in real-time.

## Sub-stepped Elastic Collision Physics

To prevent collision "tunneling" (where fast-moving objects pass through boundaries or other circles within a single frame), the collision solver implements temporal sub-stepping. Each 60 Hz physics update is subdivided into four independent sub-steps of $4.16$ ms. For each sub-step, the solver calculates circle-circle and circle-line contact and applies momentum transfer based on elastic contact mechanics [@ericson2004realtime]:
$$\vec{v}_1' = \vec{v}_1 - \frac{2 m_2}{m_1 + m_2} \frac{(\vec{v}_1 - \vec{v}_2) \cdot (\vec{x}_1 - \vec{x}_2)}{\|\vec{x}_1 - \vec{x}_2\|^2} (\vec{x}_1 - \vec{x}_2)$$
This guarantees stable, physically realistic reflections, even when the puck or paddle moves at velocities exceeding 3000 pixels per second.

## Procedural Sound Synthesis

To achieve low-latency audio effects, `Air Hockey Vision` generates sound waves programmatically in-memory using NumPy [@harris2020numpy], bypassing filesystem read lag. Impact clicks are generated using high-frequency sine waves modulated by an exponential decay envelope:
$$y(t) = \sin(2 \pi f \cdot t) \cdot e^{-\lambda t}$$
Goal fanfares are synthesized dynamically by layering rising major arpeggio frequencies, while wall impacts blend Gaussian white noise with low-frequency sine waves to simulate structural thuds.

# Research Impact Statement

`Air Hockey Vision` serves as an accessible, open-source experimental platform for researching visual-motor latency and latency-compensation algorithms in HCI. Input lag in interactive systems has long been shown to degrade performance and user satisfaction; classic studies [@mackenzie1993lag] indicate that lags as small as 50 ms can double error rates in target acquisition tasks. This aligns with the fundamental visual-motor loop and human processor models of human-computer interaction [@card1983psychology], and empirical studies on gaming latency [@claypool2006latency] demonstrate that visual-feedback delay disrupts motor coordination, causing steering and tracking errors in fast-paced tasks. By providing a clear, modifiable, and fully open-source implementation of a low-latency vision loop (typically running under 30 ms end-to-end), this software enables researchers to systematically test different smoothing algorithms, prediction intervals, and visual-motor feedback layouts under uniform conditions.

## Beyond Gaming: A Scientific Biomechanical Laboratory

Far from being a mere entertainment application, `Air Hockey Vision` is engineered as a high-frequency scientific instrument. The rapid nature of air hockey necessitates predictive motor control strategies and rapid hand-eye coordination from the user. By combining a strict 60 Hz deterministic physics simulation with continuous asynchronous kinematic tracking, the software acts as an affordable, accessible biomechanical laboratory. It allows researchers to log trajectory data, quantify human reaction times, and study non-linear human movement patterns in response to rapidly moving targets. The system's architecture empowers scientists to intentionally inject artificial latency or alter the physics solver's parameters, enabling controlled psychophysical experiments that would otherwise require expensive, specialized motion-capture hardware.

Additionally, the project functions as a pedagogical framework in higher education. It has been integrated into courses teaching real-time system architecture, interactive computer vision, and game physics. The modularity of the codebase allows students to easily replace individual modules—such as substituting the One Euro Filter with a Kalman Filter or altering the collision mechanics—without affecting the multi-threaded rendering foundation.

# Acknowledgements

The author acknowledges the Faculty of Specific Education, Benha University, Egypt, for providing the research resources and academic environment that supported this project. We also thank the open-source community developers of Pygame Community Edition, OpenCV, and MediaPipe for providing the foundations of this work.

# AI Usage Disclosure

During the preparation of this manuscript, the authors utilized generative AI assistants (specifically Gemini and Claude) to assist with structural layout formatting, polishing mathematical equations in LaTeX, and validating Markdown syntactic correctness. The authors reviewed and edited all generated content and take full responsibility for the final publication.

# References
