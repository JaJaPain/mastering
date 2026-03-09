---
name: Audio Mastering Program Skills
description: Core guidelines and architectural rules for developing the audio mastering software.
---

# Mastering Program Development Guidelines

When working in this repository, adhere strictly to the following core requirements and architectural constraints:

## 1. Core Audio Processing Requirements
- **Audio Data Format:** You must use **32-bit float or 64-bit float** representations for ALL audio processing stages. This is critical to prevent clipping during intermediate DSP operations and to maintain maximum dynamic range.
- **DSP Libraries:** Prioritize high-performance DSP libraries. Rely heavily on `numpy` for fast vectorized array operations and `scipy.signal` for filtering and complex signal processing algorithms.
- **Output Normalization:** By default, all final audio output MUST be peak-normalized to **-1.0 dBFS** to ensure safe headroom before final export or playback.

## 2. Proposed Project Folder Structure
To ensure clean, maintainable code, strictly separate the Audio Engine from the User Interface. 

```text
C:\Users\abejh\Mastering-Program-V1\
├── engine/                 # Audio Engine (Core DSP and Processing)
│   ├── __init__.py
│   ├── dsp/                # Signal processing algorithms (EQ, Compression, Limiting, etc.)
│   ├── io/                 # Audio file loading, saving, and formatting
│   └── utils.py            # DSP helpers (e.g., peak normalization functions)
├── ui/                     # User Interface (Frontend components)
│   ├── __init__.py
│   ├── components/         # Reusable functional widgets (knobs, meters, sliders)
│   ├── views/              # Main application screens and layouts
│   └── controller.py       # Intermediary bridge logic between UI actions and the Engine
├── tests/                  # Automated Testing
│   ├── test_engine/        # DSP logic and math validation tests
│   └── test_ui/            # UI unit tests
├── main.py                 # Application entry point
└── requirements.txt        # Project dependencies (e.g., numpy, scipy, pyqt/tkinter)
```

**Architectural Rule:** The `engine/` module must NEVER import from or depend on the `ui/` module. The engine must remain entirely headless and UI-agnostic to allow for easy automated testing and potential CLI usage.
