# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-03-05

### Added
- **GPU VRAM Detection**: The application now automatically detects the available GPU VRAM on startup using `nvidia-smi`.
- **Intelligent Model Suggestion**: FluidText AI now automatically evaluates the available VRAM out-of-the-box and suggests the optimal Whisper model size (from `base` to `large-v3`) based on hardware constraints. This auto-selection runs once for new users, significantly improving the onboarding experience for users with differing capabilities.
- **VRAM Display**: The system settings pane in the dashboard now explicitly shows the detected VRAM alongside the device count.
- **Push-to-Talk Dictation**: Hold a configurable hotkey, speak, and text appears at your cursor.
- **Local Whisper Inference**: GPU-accelerated transcription via faster-whisper (CTranslate2) — no cloud, no subscriptions.
- **Sleek Overlay**: Minimal, draggable waveform visualizer showing recording status.
- **System Tray Integration**: Runs quietly in the taskbar with tray menu controls.
- **Windows Autostart**: Optionally launches silently on boot via Start Menu shortcut.
- **Multi-Language Support**: 90+ languages via Whisper (German, English, French, Spanish, and more).
- **Built-in Model Manager**: Download and switch Whisper models directly from the dashboard.
- **Settings Dashboard**: Modern dark-themed UI for configuring model, language, hotkey, and autostart.
- **CPU Fallback**: Automatic fallback to CPU mode (int8 quantization) if no CUDA GPU is found.
