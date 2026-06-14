# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **macOS (Apple Silicon) support**: FluidText now runs on M-series Macs. A new
  platform layer (`execution/platform_support/`) selects the right backend per OS:
  - **Transcription** via Apple's **MLX** (`mlx-whisper`) — GPU/Neural-Engine accelerated.
  - **Global hotkey + text injection** via `pynput`.
  - **Autostart** via a LaunchAgent (`~/Library/LaunchAgents`).
  - See `requirements-mac.txt` and the macOS setup section in the README.
- **`large-v3-turbo` model**: New recommended default — near `large-v3` accuracy at ~6 GB VRAM and several times faster. VRAM auto-suggestion now prefers it for capable GPUs.
- **Custom vocabulary & corrections**: A "Custom Words" box in the dashboard lets you bias recognition toward names/jargon and define permanent corrections (`misheard => correct`) that are applied to every transcription.
- **Voice activity detection (VAD)**: Non-speech (silence/breath) is filtered before transcription, eliminating most phantom/hallucinated words on push-to-talk.

### Changed
- **Autostart now uses the registry** (`HKCU\...\Run`) instead of a Start Menu `.lnk`. The previous approach depended on `winshell`/`pywin32` DLLs and failed silently when they were missing from the build. The new path uses only the standard library and reliably launches on boot. Legacy `.lnk` shortcuts are cleaned up automatically.

### Fixed
- **Can't reopen the dashboard from the tray**: Switching between the overlay and the settings dashboard used nested `mainloop()` calls, which hung the tray "Settings"/"Restart Overlay" actions once the app was running. Window switching is now driven by a single top-level loop (queue next view → let the current mainloop exit), so the tray menu reliably reopens the dashboard. Benign Tcl teardown errors in the console are suppressed.
- **Model downloads for non-Systran repos**: The downloader now resolves the Hugging Face repo from faster-whisper's registry, so models like `large-v3-turbo` (hosted by `mobiuslabsgmbh`) download correctly.
- **Crash/debug logs** are written to the per-user data directory instead of the working directory, so they're captured even when launched at boot (where the CWD may be read-only).

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
