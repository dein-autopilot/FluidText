# Contributing to FluidText

Thank you for your interest in contributing to FluidText! 🎙️

## Getting Started

1. **Fork** the repository
2. **Clone** your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/FluidText.git
   cd FluidText
   ```
3. **Create a virtual environment:**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   ```
4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
5. **Verify setup:**
   ```bash
   python execution/verify_setup.py
   ```

## Development

### Running the App

```bash
python execution/main.py
```

### Building the Executable

```bash
python build.py
```

The output will be in `dist/FluidText/FluidText.exe`.

### Project Structure

All application code lives in the `execution/` directory:

- `main.py` — Entry point and application controller
- `gui_dashboard.py` — Settings dashboard (customtkinter)
- `gui_overlay.py` — Waveform overlay window
- `transcriber.py` — Whisper model loading and inference
- `audio_capture.py` — Microphone input
- `injector.py` — Text injection via keyboard simulation
- `settings_manager.py` — JSON settings persistence
- `utils.py` — Hotkey normalization utilities

## Pull Request Process

1. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. **Make your changes** — Keep commits focused and descriptive.
3. **Test your changes** — Run the app and verify your feature works.
4. **Push** and open a Pull Request against `main`.
5. **Describe** what your PR does and why.

## Code Style

- Use Python 3.10+ syntax
- Follow PEP 8 for formatting
- Use descriptive variable and function names
- Add comments for non-obvious logic
- Keep functions focused — one function, one responsibility

## Reporting Bugs

- Open an [issue](https://github.com/dein-autopilot/FluidText/issues) with:
  - Steps to reproduce
  - Expected vs. actual behavior
  - Your OS version, Python version, and GPU model
  - Any error logs (`crash_log.txt`, `launch_crash.txt`)

## Feature Requests

Open an issue with the `enhancement` label. Please describe:
- What problem the feature solves
- How you envision it working
- Any alternatives you've considered

## Security

If you find a security vulnerability, **do not open a public issue**. See [SECURITY.md](SECURITY.md) for responsible disclosure instructions.
