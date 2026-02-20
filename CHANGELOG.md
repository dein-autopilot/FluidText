# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **GPU VRAM Detection**: The application now automatically detects the available GPU VRAM on startup using `nvidia-smi`.
- **Intelligent Model Suggestion**: FluidText AI now automatically evaluates the available VRAM out-of-the-box and suggests the optimal Whisper model size (from `base` to `large-v3`) based on hardware constraints. This auto-selection runs once for new users, significantly improving the onboarding experience for users with differing capabilities.
- **VRAM Display**: The system settings pane in the dashboard now explicitly shows the detected VRAM alongside the device count.
