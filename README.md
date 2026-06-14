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

FluidText is a **local, GPU-accelerated voice dictation tool** for **Windows and macOS (Apple Silicon)**. Hold a hotkey, speak, and your words are typed instantly into any application — no internet required after model download. A privacy-first alternative to cloud transcription services.

Under the hood it uses the fastest local Whisper backend for your hardware:
- **Windows / Linux:** [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2) on NVIDIA GPUs (CPU fallback available).
- **macOS (M1–M4):** [MLX](https://github.com/ml-explore/mlx) (`mlx-whisper`), accelerated on the Apple Silicon GPU / Neural Engine.

## Features

- 🔒 **100% Local & Private** — Your voice never leaves your machine. No cloud APIs, no telemetry, no data collection.
- ⚡ **GPU-Accelerated** — Real-time transcription on NVIDIA GPUs with CUDA (CPU fallback available).
- 🎯 **Push-to-Talk** — Hold your configurable hotkey, speak, release. Text appears at your cursor.
- 🎨 **Sleek Overlay** — A minimal, draggable waveform visualizer shows recording status.
- 🔧 **System Tray Integration** — Runs quietly in your taskbar. No window clutter.
- 🚀 **Windows Autostart** — Optionally launches silently on boot, ready when you are.
- 🌍 **Multi-Language** — Supports 90+ languages via Whisper (German, English, French, Spanish, and more).
- 📦 **Built-in Model Manager** — Download and switch Whisper models directly from the dashboard.
- 📖 **Custom Words & Corrections** — Teach FluidText names and jargon, and define permanent fixes (`misheard => correct`) that are applied to every transcription.

## Requirements

| Component  | Windows / Linux                                  | macOS                                  |
|------------|--------------------------------------------------|----------------------------------------|
| **OS**     | Windows 10 / 11 (64-bit)                        | macOS 13+ on **Apple Silicon** (M1–M4) |
| **Python** | 3.10 or higher                                   | 3.10 or higher                         |
| **Accel.** | NVIDIA GPU + CUDA 12.x (6+ GB VRAM recommended)  | Apple Silicon GPU via MLX (built-in)   |

> **Note (Windows/Linux):** The app falls back to CPU mode (`int8` quantization) if no compatible NVIDIA GPU is found, but transcription will be significantly slower.
>
> **Note (macOS):** Only Apple Silicon (M-series) is supported — `mlx-whisper` does not run on Intel Macs.

## Installation

### Option A: Download the Executable (Recommended)

Download the latest release from the [Releases](https://github.com/dein-autopilot/FluidText/releases) page. No Python installation required.

### Option B: Run from Source — Windows

```powershell
# 1. Clone the repository
git clone https://github.com/dein-autopilot/FluidText.git
cd FluidText

# 2. Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1     # PowerShell  (or: venv\Scripts\activate.bat in cmd)

# 3. Install dependencies
pip install -r requirements.txt

# 4. Verify your setup (optional) and run
python execution/verify_setup.py
python execution/main.py
```

### Option B: Run from Source — macOS (Apple Silicon)

```bash
# 1. Clone the repository
git clone https://github.com/dein-autopilot/FluidText.git
cd FluidText

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install the macOS dependencies (MLX backend, pynput, pyobjc)
pip install -r requirements-mac.txt

# 4. Run
python execution/main.py
```

> **⚠️ Grant macOS permissions (required).** The first time you use the hotkey/typing,
> macOS will block it until you allow your terminal (or the built app) under:
> **System Settings → Privacy & Security →**
> - **Input Monitoring** — so FluidText can detect the push-to-talk hotkey.
> - **Accessibility** — so FluidText can type the transcribed text into other apps.
>
> Toggle both on, then quit and relaunch the app. Without these, the hotkey and
> text injection silently do nothing.

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
- **Add custom words** — bias recognition toward names/jargon, and add `misheard => correct` lines to permanently fix recurring mistakes
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
| `medium`         | ~1.5 GB | ~5 GB  | ⚡⚡       | ★★★★☆    |
| `large-v3-turbo` | ~1.6 GB | ~6 GB  | ⚡⚡⚡⚡   | ★★★★★    |
| `large-v2`       | ~3 GB   | ~10 GB | ⚡         | ★★★★★    |
| `large-v3`       | ~3 GB   | ~10 GB | ⚡         | ★★★★★    |

> **Recommendation:** Use `large-v3-turbo` — it delivers near `large-v3` accuracy at a fraction of the VRAM and is several times faster. Drop to `small`/`medium` only on low-VRAM GPUs, or use `large-v3` if you need the last bit of accuracy and have 10+ GB VRAM.

Models are downloaded from [Hugging Face](https://huggingface.co/Systran) on first use and cached locally in your user data directory.

> **On macOS** the same model names map to their **MLX** equivalents (e.g. `large-v3-turbo` → [`mlx-community/whisper-large-v3-turbo`](https://huggingface.co/mlx-community/whisper-large-v3-turbo)) and are cached in the shared Hugging Face cache (`~/.cache/huggingface`).

### Manual Model Download

If you're behind a firewall or prefer offline setup:

1. Visit the model page (e.g., [Systran/faster-whisper-large-v3](https://huggingface.co/Systran/faster-whisper-large-v3))
2. Download all files from the repository
3. Place them in your local model directory:
   - Windows: `C:\Users\<you>\AppData\Local\FluidText\FluidTextAI\models\large-v3\`

## Building an Executable

### Windows (`.exe`)

```powershell
python build.py
```

The output will be in `dist/FluidText/FluidText.exe`.

> **Note:** Building requires all dependencies installed plus PyInstaller. The build script handles NVIDIA DLL bundling automatically.

### macOS (`.app`)

A PyInstaller one-file/app bundle can be produced directly (after installing
`requirements-mac.txt` + `pyinstaller`):

```bash
pyinstaller --windowed --name FluidText \
  --hidden-import platform_support.hotkey_mac \
  --hidden-import platform_support.autostart_mac \
  --collect-all mlx_whisper \
  --add-data "execution/assets:assets" \
  execution/main.py
```

> Distributing a `.app` to other Macs additionally requires **code signing &
> notarization** with an Apple Developer ID — otherwise Gatekeeper blocks it.
> Running locally on your own machine does not.

## Project Structure

```
FluidText/
├── execution/
│   ├── main.py              # Application entry point & controller
│   ├── transcriber.py       # Whisper model loading & inference
│   ├── audio_capture.py     # Microphone recording (sounddevice)
│   ├── injector.py          # Text injection (keyboard on Windows, pynput on macOS)
│   ├── gui_dashboard.py     # Settings dashboard UI (customtkinter)
│   ├── gui_overlay.py       # Waveform overlay UI
│   ├── settings_manager.py  # Persistent settings (JSON, appdirs)
│   ├── utils.py             # Hotkey normalization
│   ├── verify_setup.py      # CUDA & audio hardware check
│   ├── platform_support/    # OS abstraction: hotkey + autostart (Windows / macOS)
│   ├── generate_audio.py    # UI sound generation
│   ├── generate_logo.py     # App icon generation
│   └── assets/              # Icons and audio files
├── requirements.txt         # Windows / Linux dependencies
├── requirements-mac.txt     # macOS (Apple Silicon) dependencies
├── build.py                 # PyInstaller build script (Windows)
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

Capturing global hotkeys needs low-level keyboard access: on Windows this may require running as Administrator; on macOS it requires the **Input Monitoring** and **Accessibility** permissions (see the macOS install section).

For more details, see [SECURITY.md](SECURITY.md).

## Known Limitations

- **Windows & macOS (Apple Silicon)** — Linux is not packaged (the faster-whisper backend works there, but the hotkey/autostart adapters are Windows/macOS only).
- **Acceleration is hardware-specific** — NVIDIA GPUs (CUDA) on Windows/Linux, Apple Silicon (MLX) on macOS. AMD/Intel GPUs are not accelerated; CPU mode is available on Windows/Linux but much slower. Intel Macs are unsupported.
- **Elevated permissions for hotkeys** — Windows may need Administrator; macOS needs Input Monitoring + Accessibility.
- **Single monitor** — The overlay positions itself relative to the primary display.
- **No streaming transcription** — Audio is transcribed after you release the hotkey (not in real-time while speaking).

## Troubleshooting

| Problem | Solution |
|---------|----------|
| **Model download stuck at 0%** | Check your internet connection. If behind a corporate firewall, download the model manually (see above). |
| **"CUDA not available" error** | Ensure you have an NVIDIA GPU and that `nvidia-cublas-cu12` and `nvidia-cudnn-cu12` are installed. Run `python execution/verify_setup.py` to diagnose. |
| **Hotkey not working (Windows)** | Try running the app as Administrator. The `keyboard` library requires elevated privileges on some systems. |
| **Hotkey/typing not working (macOS)** | Grant **Input Monitoring** *and* **Accessibility** to your terminal/app in System Settings → Privacy & Security, then relaunch. |
| **Text not appearing** | Ensure your cursor is in a text input field. Some applications block simulated keyboard input. |
| **App crashes on startup** | Check the logs in your user data dir: Windows `…\AppData\Local\FluidText\FluidTextAI\logs\`, macOS `~/Library/Application Support/FluidText/logs/`. |

## License

This project is licensed under the [MIT License](LICENSE).

---

<p align="center">
  <sub>Built with ❤️ for privacy-conscious users who want fast, local voice dictation.</sub>
</p>
