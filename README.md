# High-Fidelity Mastering Console v1

A professional-grade, locally-hosted python audio mastering environment designed to deliver loud, clear, and competitively balanced tracks.

## Core Features

- **64-bit Floating Point DSP Chain**: The entire audio processing pipeline operates in pure 64-bit precision (`np.float64`), offering virtually infinite headroom and preventing any internal digital clipping before the final output stage.
- **Linear Phase EQ**: A specialized zero-phase-shift equalizer designed specifically for mastering. It allows you to add brilliant 'Air' (12kHz shelf) and tightly roll off sub-rumble without introducing phase smearing or artificial coloration.
- **Analog-Style Soft Saturation**: Emulates the harmonic richness of analog gear using a tangential (`tanh`) soft-clipping drive curve, increasing perceived loudness without harsh, squared-off digital distortion.
- **True Peak Limiter (4x Oversampled)**: Capable of catching inter-sample peaks (ISPs) that normal limiters miss, ensuring your audio strictly adheres to true-peak limits (e.g., -1.0 dBFS) across all playback systems.
- **Broadcast-Standard Loudness (LUFS)**: Built-in ITU-R BS.1770-4 compliant loudness normalization guarantees your masters hit exact loudness targets (e.g., -14 LUFS for Spotify/YouTube) effortlessly upon export.
- **Real-time A/B Previewing & Visualization**: Includes an immediate A/B toggle and a blazingly fast native-Tkinter waveform canvas to visually and audibly compare your dry and wet signals instantly.
- **Dynamic Preset Manager**: Ships with 20 genre-tailored starting points (from Djent to Dream Pop) to instantly recall the perfect balance of Drive, EQ, and Target LUFS.

## Built With
- `numpy` & `scipy`: For high-performance arrays and signal processing.
- `pyloudnorm`: For standard-compliant loudness measurements.
- `sounddevice`: For low-latency audio buffering and playback.
- `tkinter`: For a lightweight, responsive, and native desktop GUI.
