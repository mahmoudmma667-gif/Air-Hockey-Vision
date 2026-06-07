# Contributing to Air Hockey Vision

Thank you for your interest in contributing to **Air Hockey Vision**. We welcome contributions from research scientists, developers, students, and practitioners in human-computer interaction (HCI), computer vision, and game development.

By contributing, you help make real-time gesture control technology more stable, accessible, and educational for the community.

---

## Areas of Contribution

You can contribute in several ways:
1.  **Bug Reports**: Open an issue if you encounter crashes, coordinate jitter, or webcam device incompatibility.
2.  **Feature Requests**: Propose enhancements such as support for multi-hand control, advanced physics parameters, or new rendering themes.
3.  **Code Contributions**:
    *   Optimizations for hand landmark processing threads.
    *   Improved predictive kinematics for latency compensation.
    *   New automated test cases covering physics, AI behavior, or menu logic.
4.  **Academic Enhancements**: Improving paper documentation, bibliographic records, or visual assets.

---

## Development Workflow

To submit code changes, please follow the steps outlined below:

### 1. Fork and Clone
Fork the repository on GitHub, then clone the repository locally:
```bash
git clone https://github.com/mahmoudlabib/air-hockey-vision.git
cd air-hockey-vision
```

### 2. Set Up a Virtual Environment
We recommend using a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install pytest
```

### 3. Implement Your Changes
Ensure your code adheres to standard PEP 8 styles and is fully documented in professional Academic English (especially mathematical functions and signal processing loops).

### 4. Run Automated Tests
Before submitting a pull request, run the test suite to verify no regressions were introduced:
```bash
pytest test_main.py
```

### 5. Submit a Pull Request
Push your changes to your fork and open a Pull Request (PR) against the `main` branch. Provide a detailed summary of what your change addresses and any mathematical foundations or architectural integrations involved.

---

## Questions & Discussion
If you have questions about the mathematical models (such as the One Euro Filter coefficients, physics substeps, or arpeggiator envelopes), feel free to open a GitHub Discussion or contact the maintainers directly.
