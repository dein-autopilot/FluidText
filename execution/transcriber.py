
import os
import sys
import site
import subprocess
import numpy as np

IS_MAC = sys.platform == "darwin"

# faster-whisper model id -> mlx-community repo (used on Apple Silicon).
MLX_REPOS = {
    "tiny": "mlx-community/whisper-tiny",
    "base": "mlx-community/whisper-base",
    "small": "mlx-community/whisper-small",
    "medium": "mlx-community/whisper-medium",
    "large-v2": "mlx-community/whisper-large-v2",
    "large-v3": "mlx-community/whisper-large-v3",
    "large-v3-turbo": "mlx-community/whisper-large-v3-turbo",
}

# ── Force-load NVIDIA DLLs (Windows CUDA) BEFORE faster_whisper/ctranslate2 ──
# Not needed on macOS (Apple Silicon uses the MLX backend, no CUDA).
if not IS_MAC and os.name == 'nt':
    try:
        # Check if we are running in a PyInstaller bundle
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS
            os.add_dll_directory(base_dir)
            os.environ['PATH'] = base_dir + os.pathsep + os.environ['PATH']

            nvidia_path = os.path.join(base_dir, 'nvidia')
            if os.path.exists(nvidia_path):
                cublas_bin = os.path.join(nvidia_path, 'cublas', 'bin')
                cudnn_bin = os.path.join(nvidia_path, 'cudnn', 'bin')
                if os.path.exists(cublas_bin): os.add_dll_directory(cublas_bin)
                if os.path.exists(cudnn_bin): os.add_dll_directory(cudnn_bin)

            print("[INFO] Frozen mode: Added sys._MEIPASS to DLL search path.")
        else:
            found_nvidia = False
            for site_pkg in site.getsitepackages():
                nvidia_path = os.path.join(site_pkg, 'nvidia')
                if os.path.exists(nvidia_path):
                    cublas_bin = os.path.join(nvidia_path, 'cublas', 'bin')
                    cudnn_bin = os.path.join(nvidia_path, 'cudnn', 'bin')

                    if os.path.exists(cublas_bin):
                        os.add_dll_directory(cublas_bin)
                        os.environ['PATH'] = cublas_bin + os.pathsep + os.environ['PATH']
                        print(f"[INFO] Added DLL dir to PATH: {cublas_bin}")
                        found_nvidia = True

                    if os.path.exists(cudnn_bin):
                        os.add_dll_directory(cudnn_bin)
                        os.environ['PATH'] = cudnn_bin + os.pathsep + os.environ['PATH']
                        print(f"[INFO] Added DLL dir to PATH: {cudnn_bin}")

            if not found_nvidia:
                print("[WARN] Could not find 'nvidia' directory in site-packages.")

    except Exception as e:
        print(f"[WARN] Failed to add NVIDIA DLLs: {e}")

import glob


def check_nvidia_dlls():
    """Diagnose the available transcription accelerator.

    On Windows/Linux this checks CUDA + the required NVIDIA DLLs. On macOS it
    reports the MLX (Apple Silicon) backend instead. The dashboard renders the
    result; ``is_mac`` tells it which wording to use.
    """
    if IS_MAC:
        return _check_apple_silicon()

    results = {
        'cuda_available': False,
        'cuda_device_count': 0,
        'cublas': False,
        'cublaslt': False,
        'cudnn': False,
        'vram_mb': 0,
        'is_mac': False,
        'details': {},
    }

    # 0. Check VRAM via nvidia-smi
    try:
        creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        output = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            creationflags=creation_flags, text=True
        )
        vram_mb = int(output.strip().split('\n')[0])
        results['vram_mb'] = vram_mb
    except Exception as e:
        results['details']['nvidia-smi'] = str(e)

    # 1. Check ctranslate2 CUDA support
    try:
        import ctranslate2
        count = ctranslate2.get_cuda_device_count()
        results['cuda_available'] = count > 0
        results['cuda_device_count'] = count
    except Exception as e:
        results['details']['ctranslate2'] = str(e)

    # 2. Build list of directories to search for DLLs
    search_dirs = []

    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
        search_dirs.append(base)
        nvidia_path = os.path.join(base, 'nvidia')
        if os.path.exists(nvidia_path):
            for sub in ('cublas', 'cudnn', 'cublasLt'):
                bin_path = os.path.join(nvidia_path, sub, 'bin')
                if os.path.exists(bin_path):
                    search_dirs.append(bin_path)
    else:
        try:
            for site_pkg in site.getsitepackages():
                nvidia_path = os.path.join(site_pkg, 'nvidia')
                if os.path.exists(nvidia_path):
                    for sub in ('cublas', 'cudnn', 'cublasLt'):
                        bin_path = os.path.join(nvidia_path, sub, 'bin')
                        if os.path.exists(bin_path):
                            search_dirs.append(bin_path)
        except Exception:
            pass

    path_dirs = os.environ.get('PATH', '').split(os.pathsep)
    search_dirs.extend(path_dirs)

    # 3. Search for specific DLLs
    dll_patterns = {
        'cublas':   'cublas64_*.dll',
        'cublaslt': 'cublasLt64_*.dll',
        'cudnn':    'cudnn64_*.dll',
    }
    cudnn_alt_patterns = ['cudnn_ops_*.dll', 'cudnn_cnn_*.dll', 'cudnn64_*.dll']

    for dll_key, pattern in dll_patterns.items():
        found = False
        for d in search_dirs:
            if not os.path.isdir(d):
                continue
            matches = glob.glob(os.path.join(d, pattern))
            if matches:
                results[dll_key] = True
                results['details'][dll_key] = matches[0]
                found = True
                break
        if not found and dll_key == 'cudnn':
            for alt in cudnn_alt_patterns:
                for d in search_dirs:
                    if not os.path.isdir(d):
                        continue
                    matches = glob.glob(os.path.join(d, alt))
                    if matches:
                        results['cudnn'] = True
                        results['details']['cudnn'] = matches[0]
                        found = True
                        break
                if found:
                    break
        if not found:
            results['details'][dll_key] = 'Not found'

    return results


def _check_apple_silicon():
    """Report MLX availability and unified memory on macOS."""
    results = {
        'cuda_available': False, 'cuda_device_count': 0,
        'cublas': False, 'cublaslt': False, 'cudnn': False,
        'vram_mb': 0, 'is_mac': True, 'mlx_available': False,
        'details': {},
    }
    try:
        import mlx_whisper  # noqa: F401
        results['mlx_available'] = True
        # Treat MLX as an "accelerator" so the dashboard's model auto-suggest
        # and ready-state logic light up just like CUDA does.
        results['cuda_available'] = True
        results['cuda_device_count'] = 1
    except Exception as e:
        results['details']['mlx'] = str(e)

    try:
        out = subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True)
        results['vram_mb'] = int(out.strip()) // (1024 * 1024)
    except Exception as e:
        results['details']['sysctl'] = str(e)

    return results


class Transcriber:
    def __init__(self, model_size="large-v3", device="cuda", language="de",
                 vocabulary=None, replacements=None):
        self.model_size = model_size
        self.device = device
        self.language = language if language != "auto" else None
        self.model = None
        self._backend = None
        self._mlx_repo = None
        # Custom vocabulary biases Whisper toward the user's preferred spelling
        # of names/jargon. Replacements are applied verbatim after transcription
        # ("learned" corrections: fix once, fixed forever).
        self.set_vocabulary(vocabulary, replacements)

    def set_vocabulary(self, vocabulary=None, replacements=None):
        self.vocabulary = list(vocabulary) if vocabulary else []
        self.replacements = dict(replacements) if replacements else {}
        if self.vocabulary:
            # Whisper's initial_prompt is most effective as a short, natural
            # phrase. Cap it so we don't crowd out the actual audio context.
            words = ", ".join(self.vocabulary)[:400]
            self.initial_prompt = f"Glossar: {words}."
        else:
            self.initial_prompt = None

    def apply_replacements(self, text):
        """Apply user-defined word corrections, case-insensitively but
        preserving the replacement's own casing."""
        if not text or not self.replacements:
            return text
        import re
        for wrong, right in self.replacements.items():
            if not wrong:
                continue
            # \b around the term so we replace whole words, not substrings.
            pattern = r"\b" + re.escape(wrong) + r"\b"
            text = re.sub(pattern, right, text, flags=re.IGNORECASE)
        return text

    # ── Loading ──────────────────────────────────────────────────────────
    def load_model(self):
        if IS_MAC:
            self._load_mlx()
        else:
            self._load_faster_whisper()

    def _load_mlx(self):
        """Apple Silicon backend. MLX runs Whisper on the M-series GPU."""
        try:
            import mlx_whisper  # noqa: F401
            self._backend = "mlx"
            self._mlx_repo = MLX_REPOS.get(
                self.model_size, f"mlx-community/whisper-{self.model_size}")
            print(f"Loading MLX Whisper model: {self._mlx_repo}")
            # Pre-fetch the weights so the first dictation isn't slow and works
            # offline afterwards. mlx_whisper otherwise downloads lazily.
            try:
                from huggingface_hub import snapshot_download
                snapshot_download(self._mlx_repo)
            except Exception as e:
                print(f"[WARN] Could not pre-fetch MLX model: {e}")
            self.device = "mlx"
            self.model = True  # readiness marker (mlx loads per-call internally)
            print("MLX backend ready.")
        except Exception as e:
            print(f"[WARN] MLX unavailable ({e}); falling back to faster-whisper CPU.")
            self._load_faster_whisper(force_cpu=True)

    def _load_faster_whisper(self, force_cpu=False):
        from faster_whisper import WhisperModel
        self._backend = "faster-whisper"
        device = "cpu" if force_cpu else self.device
        print(f"Loading Whisper Model: {self.model_size} on {device}")

        # Resolve local model path first (persists across builds)
        import appdirs
        user_data = appdirs.user_data_dir("FluidText", "FluidTextAI")
        local_model_path = os.path.join(user_data, "models", self.model_size)

        model_to_load = self.model_size
        if os.path.exists(os.path.join(local_model_path, "config.json")):
            print(f"Found local model at: {local_model_path}")
            model_to_load = local_model_path

        compute = "int8" if device == "cpu" else "float16"
        try:
            self.model = WhisperModel(model_to_load, device=device, compute_type=compute)
            print("Model object created. Testing inference...")

            # Test inference with 1s of silence to catch runtime errors
            # (e.g., cublas64_12.dll missing — model loads fine but encode() crashes)
            test_audio = np.zeros(16000, dtype=np.float32)
            segments, info = self.model.transcribe(test_audio, beam_size=1)
            for _ in segments:
                pass
            self.device = device
            print(f"Model loaded and verified on {device}.")

        except Exception as e:
            print(f"Error with {device}: {e}")
            if device == "cuda":
                print("Falling back to CPU (int8)...")
                self.device = "cpu"
                try:
                    self.model = WhisperModel(model_to_load, device="cpu", compute_type="int8")
                    test_audio = np.zeros(16000, dtype=np.float32)
                    segments, info = self.model.transcribe(test_audio, beam_size=1)
                    for _ in segments:
                        pass
                    print("Model loaded and verified on CPU.")
                except Exception as e2:
                    print(f"CPU fallback also failed: {e2}")
                    self.model = None
            else:
                self.model = None

    # ── Inference ────────────────────────────────────────────────────────
    def transcribe(self, audio_data):
        """audio_data: numpy array of float32 (16 kHz mono)."""
        if self.model is None:
            print("[ERROR] Model not loaded!")
            return ""
        if self._backend == "mlx":
            return self._transcribe_mlx(audio_data)
        return self._transcribe_faster_whisper(audio_data)

    def _transcribe_faster_whisper(self, audio_data):
        print(f"[DEBUG] Starting transcription on {len(audio_data)} samples...")
        try:
            # vad_filter: drop non-speech (silence/breath) so Whisper doesn't
            #   hallucinate phantom words on quiet push-to-talk recordings.
            # initial_prompt: bias toward the user's custom vocabulary.
            segments, info = self.model.transcribe(
                audio_data,
                beam_size=5,
                language=self.language,
                vad_filter=True,
                initial_prompt=self.initial_prompt,
            )

            print(f"[DEBUG] Model detected language '{info.language}' with probability {info.language_probability}")

            full_text = ""
            segment_count = 0
            for segment in segments:
                print(f"[DEBUG] Segment found: {segment.text}")
                full_text += segment.text
                segment_count += 1

            full_text = self.apply_replacements(full_text.strip())
            print(f"[DEBUG] Transcription finished. Segments: {segment_count}. Text: {full_text}")
            return full_text
        except Exception as e:
            print(f"[ERROR] Logic Error in Transcribe: {e}")
            import traceback
            traceback.print_exc()
            return ""

    def _transcribe_mlx(self, audio_data):
        print(f"[DEBUG] Starting MLX transcription on {len(audio_data)} samples...")
        try:
            import mlx_whisper
            result = mlx_whisper.transcribe(
                audio_data,
                path_or_hf_repo=self._mlx_repo,
                language=self.language,
                initial_prompt=self.initial_prompt,
            )
            full_text = self.apply_replacements((result.get("text") or "").strip())
            print(f"[DEBUG] MLX transcription finished. Text: {full_text}")
            return full_text
        except Exception as e:
            print(f"[ERROR] Logic Error in MLX Transcribe: {e}")
            import traceback
            traceback.print_exc()
            return ""
