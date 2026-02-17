<p align="center">
  <h1 align="center">🎙️ FluidText</h1>
  <p align="center">
    <strong>Real-time voice-to-text, powered by AI. Runs locally. No cloud. No subscriptions.</strong>
  </p>
  <p align="center">
    <a href="#features">Features</a> •
    <a href="#requirements">Requirements</a> •
    <a href="#installation">Installation</a> •
    <a href="#usage">Usage</a> •
    <a href="#building-an-executable">Build</a> •
    <a href="#known-limitations">Limitations</a> •
    <a href="#license">License</a>
  </p>
</p>

---

FluidText is a **local, GPU-accelerated voice dictation tool** for Windows. Hold a hotkey, speak, and your words are typed instantly into any application — no internet required after model download. A privacy-first alternative to cloud transcription services.

Built on [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2) for blazing-fast inference on consumer NVIDIA GPUs.

## Features

- 🔒 **100% Local & Private** — Your voice never leaves your machine. No cloud APIs, no telemetry, no data collection.
- ⚡ **GPU-Accelerated** — Real-time transcription on NVIDIA GPUs with CUDA (CPU fallback available).
- 🎯 **Push-to-Talk** — Hold your configurable hotkey, speak, release. Text appears at your cursor.
- 🎨 **Sleek Overlay** — A minimal, draggable waveform visualizer shows recording status.
- 🔧 **System Tray Integration** — Runs quietly in your taskbar. No window clutter.
- 🚀 **Windows Autostart** — Optionally launches silently on boot, ready when you are.
- 🌍 **Multi-Language** — Supports 90+ languages via Whisper (German, English, French, Spanish, and more).
- 📦 **Built-in Model Manager** — Download and switch Whisper models directly from the dashboard.

## Requirements

| Component  | Minimum                                          |
|------------|--------------------------------------------------|
| **OS**     | Windows 10 / 11 (64-bit)                        |
| **Python** | 3.10 or higher (for running from source)         |
| **GPU**    | NVIDIA GPU with CUDA support (6+ GB VRAM recommended) |
| **CUDA**   | CUDA 12.x (installed automatically via pip)      |

> **Note:** The app falls back to CPU mode (`int8` quantization) if no compatible GPU is found, but transcription will be significantly slower.

## Installation

### Option A: Download the Executable (Recommended)

Download the latest release from the [Releases](https://github.com/dein-autopilot/FluidText/releases) page. No Python installation required.

### Option B: Run from Source

```bash
# 1. Clone the repository
git clone https://github.com/dein-autopilot/FluidText.git
cd FluidText

# 2. Create a virtual environment
python -m venv venv

# 3. Activate it
venv\Scripts\activate        # Windows (cmd)
# or
.\venv\Scripts\Activate.ps1  # Windows (PowerShell)

# 4. Install dependencies
pip install -r requirements.txt

# 5. Verify your setup (optional)
python execution/verify_setup.py
```

## Usage

### Start the App

```bash
python execution/main.py
```

### Dashboard

On launch, the **Settings Dashboard** appears where you can:

- **Select the AI model** (tiny → large-v3) — models are downloaded automatically
- **Set your language** (German, English, auto-detect, and more)
- **Configure your push-to-talk hotkey** (default: `Right Ctrl`)
- **Enable Windows Autostart** — launches silently to the system tray on boot

Click **"Save & Start ▸"** to save your settings and launch the overlay.

### Dictating

1. **Hold** your hotkey (default: `Right Ctrl`)
2. **Speak** — the waveform visualizer reacts to your voice
3. **Release** — your speech is transcribed and typed at the cursor position

Works in **any application** — browsers, Word, Slack, code editors, etc.

### System Tray

The app lives in your system tray (bottom-right). Right-click the icon to:

- **Show Overlay** — bring back the visualizer window
- **Settings** — open the dashboard
- **Restart Overlay** — reset the overlay position
- **Quit** — exit the app

## Available Models

| Model      | Download Size | VRAM   | Speed       | Accuracy   |
|------------|--------------|--------|-------------|------------|
| `tiny`     | ~75 MB       | ~1 GB  | ⚡⚡⚡⚡⚡ | ★☆☆☆☆    |
| `base`     | ~150 MB      | ~1 GB  | ⚡⚡⚡⚡   | ★★☆☆☆    |
| `small`    | ~500 MB      | ~2 GB  | ⚡⚡⚡     | ★★★☆☆    |
| `medium`   | ~1.5 GB      | ~5 GB  | ⚡⚡       | ★★★★☆    |
| `large-v2` | ~3 GB        | ~10 GB | ⚡         | ★★★★★    |
| `large-v3` | ~3 GB        | ~10 GB | ⚡         | ★★★★★    |

> **Recommendation:** Use `large-v3` for best accuracy if your GPU has 10+ GB VRAM. Use `small` or `medium` for a good speed/accuracy tradeoff.

Models are downloaded from [Hugging Face](https://huggingface.co/Systran) on first use and cached locally in your user data directory.

### Manual Model Download

If you're behind a firewall or prefer offline setup:

1. Visit the model page (e.g., [Systran/faster-whisper-large-v3](https://huggingface.co/Systran/faster-whisper-large-v3))
2. Download all files from the repository
3. Place them in your local model directory:
   - Windows: `C:\Users\<you>\AppData\Local\FluidText\FluidTextAI\models\large-v3\`

## Building an Executable

To create a standalone `.exe` (no Python required for end users):

```bash
python build.py
```

The output will be in `dist/FluidText/FluidText.exe`.

> **Note:** Building requires all dependencies installed plus PyInstaller. The build script handles NVIDIA DLL bundling automatically.

## Project Structure

```
FluidText/
├── execution/
│   ├── main.py              # Application entry point & controller
│   ├── transcriber.py       # Whisper model loading & inference
│   ├── audio_capture.py     # Microphone recording (sounddevice)
│   ├── injector.py          # Text injection via keyboard simulation
│   ├── gui_dashboard.py     # Settings dashboard UI (customtkinter)
│   ├── gui_overlay.py       # Waveform overlay UI
│   ├── settings_manager.py  # Persistent settings (JSON, appdirs)
│   ├── utils.py             # Hotkey normalization
│   ├── verify_setup.py      # CUDA & audio hardware check
│   ├── generate_audio.py    # UI sound generation
│   ├── generate_logo.py     # App icon generation
│   └── assets/              # Icons and audio files
├── requirements.txt         # Python dependencies
├── build.py                 # PyInstaller build script
├── FluidText.spec           # PyInstaller spec file
├── LICENSE                  # MIT License
├── SECURITY.md              # Security policy
├── CONTRIBUTING.md          # Contributing guidelines
└── README.md
```

## Security & Privacy

FluidText is designed with privacy as a core principle:

- **No network access** — The app never connects to the internet during normal use. The only network activity is the initial model download from Hugging Face.
- **No telemetry** — No usage data, analytics, or crash reports are sent anywhere.
- **No cloud processing** — All speech recognition happens locally on your GPU/CPU.
- **Local storage only** — Settings and models are stored in your local user data directory.

The `keyboard` library requires elevated privileges to capture global hotkeys. This is a known requirement for push-to-talk functionality on Windows.

For more details, see [SECURITY.md](SECURITY.md).

## Known Limitations

- **Windows only** — Uses Windows-specific APIs (`ctypes.windll`, `winshell`, `pypiwin32`) for taskbar integration, autostart, and system tray. Linux/macOS support would require significant refactoring.
- **NVIDIA GPUs only for acceleration** — AMD and Intel GPUs are not supported for CUDA acceleration. CPU mode is available but much slower.
- **Requires admin/elevated privileges** — The `keyboard` library needs low-level access to monitor global hotkeys.
- **Single monitor** — The overlay positions itself relative to the primary display.
- **No streaming transcription** — Audio is transcribed after you release the hotkey (not in real-time while speaking).

## Troubleshooting

| Problem | Solution |
|---------|----------|
| **Model download stuck at 0%** | Check your internet connection. If behind a corporate firewall, download the model manually (see above). |
| **"CUDA not available" error** | Ensure you have an NVIDIA GPU and that `nvidia-cublas-cu12` and `nvidia-cudnn-cu12` are installed. Run `python execution/verify_setup.py` to diagnose. |
| **Hotkey not working** | Try running the app as Administrator. The `keyboard` library requires elevated privileges on some systems. |
| **Text not appearing** | Ensure your cursor is in a text input field. Some applications block simulated keyboard input. |
| **App crashes on startup** | Check `crash_log.txt` or `launch_crash.txt` next to the executable for error details. |

## License

This project is licensed under the [MIT License](LICENSE).

---

<p align="center">
  <sub>Built with ❤️ for privacy-conscious users who want fast, local voice dictation.</sub>
</p>
