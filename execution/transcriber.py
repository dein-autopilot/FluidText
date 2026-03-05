
import os
import sys
import site
import subprocess

# Force load NVIDIA DLLs for Windows
# MUST BE DONE BEFORE IMPORTING FASTER_WHISPER / CTRANSLATE2
# Force load NVIDIA DLLs for Windows
# MUST BE DONE BEFORE IMPORTING FASTER_WHISPER / CTRANSLATE2
if os.name == 'nt':
    try:
        # Check if we are running in a PyInstaller bundle
        if getattr(sys, 'frozen', False):
            # In frozen mode, DLLs are in sys._MEIPASS (the temp folder) or next to exe
            base_dir = sys._MEIPASS
            
            # Add base dir to DLL search path
            os.add_dll_directory(base_dir)
            os.environ['PATH'] = base_dir + os.pathsep + os.environ['PATH']
            
            # Also try to specifically add 'nvidia' subdirs if they were collected
            nvidia_path = os.path.join(base_dir, 'nvidia')
            if os.path.exists(nvidia_path):
                 cublas_bin = os.path.join(nvidia_path, 'cublas', 'bin')
                 cudnn_bin = os.path.join(nvidia_path, 'cudnn', 'bin')
                 if os.path.exists(cublas_bin): os.add_dll_directory(cublas_bin)
                 if os.path.exists(cudnn_bin): os.add_dll_directory(cudnn_bin)
                 
            print("[INFO] Frozen mode: Added sys._MEIPASS to DLL search path.")
            
        else:
            # Loop through all site-packages to find nvidia libs
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

from faster_whisper import WhisperModel
import numpy as np
import ctypes
import glob


def check_nvidia_dlls():
    """
    Check for required NVIDIA DLLs and CUDA availability.
    Returns a dict: {
        'cuda_available': bool,
        'cuda_device_count': int,
        'cublas': bool,
        'cublaslt': bool,
        'cudnn': bool,
        'vram_mb': int,
        'details': {name: path_or_error, ...}
    }
    """
    results = {
        'cuda_available': False,
        'cuda_device_count': 0,
        'cublas': False,
        'cublaslt': False,
        'cudnn': False,
        'vram_mb': 0,
        'details': {},
    }

    # 0. Check VRAM via nvidia-smi
    try:
        creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        output = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            creationflags=creation_flags, text=True
        )
        # Handle multiple GPUs by taking the first one
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
        # PyInstaller bundle
        base = sys._MEIPASS
        search_dirs.append(base)
        nvidia_path = os.path.join(base, 'nvidia')
        if os.path.exists(nvidia_path):
            for sub in ('cublas', 'cudnn', 'cublasLt'):
                bin_path = os.path.join(nvidia_path, sub, 'bin')
                if os.path.exists(bin_path):
                    search_dirs.append(bin_path)
    else:
        # Dev mode: look in site-packages
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

    # Also search PATH
    path_dirs = os.environ.get('PATH', '').split(os.pathsep)
    search_dirs.extend(path_dirs)

    # 3. Search for specific DLLs
    dll_patterns = {
        'cublas':   'cublas64_*.dll',
        'cublaslt': 'cublasLt64_*.dll',
        'cudnn':    'cudnn64_*.dll',
    }

    # Also accept cudnn_ops_*, cudnn_cnn_*, etc. (newer cudnn ships split DLLs)
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
            # Try alternative cudnn patterns
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


class Transcriber:
    def __init__(self, model_size="large-v3", device="cuda", language="de"):
        self.model_size = model_size
        self.device = device
        self.language = language if language != "auto" else None
        self.model = None

    def load_model(self):
        print(f"Loading Whisper Model: {self.model_size} on {self.device}")
        
        # Resolve local model path first (persists across builds)
        import appdirs
        user_data = appdirs.user_data_dir("FluidText", "FluidTextAI")
        local_model_path = os.path.join(user_data, "models", self.model_size)
        
        model_to_load = self.model_size
        if os.path.exists(os.path.join(local_model_path, "config.json")):
            print(f"Found local model at: {local_model_path}")
            model_to_load = local_model_path
        
        try:
            self.model = WhisperModel(model_to_load, device=self.device, compute_type="float16")
            print("Model object created. Testing inference...")
            
            # Test inference with 1s of silence to catch runtime errors
            # (e.g., cublas64_12.dll missing — model loads fine but encode() crashes)
            test_audio = np.zeros(16000, dtype=np.float32)
            segments, info = self.model.transcribe(test_audio, beam_size=1)
            # Force the generator to execute (segments is lazy)
            for _ in segments:
                pass
            print(f"Model loaded and verified on {self.device}.")
            
        except Exception as e:
            print(f"Error with {self.device}: {e}")
            if self.device == "cuda":
                print("Falling back to CPU (int8)...")
                self.device = "cpu"
                try:
                    self.model = WhisperModel(model_to_load, device="cpu", compute_type="int8")
                    # Also test CPU inference
                    test_audio = np.zeros(16000, dtype=np.float32)
                    segments, info = self.model.transcribe(test_audio, beam_size=1)
                    for _ in segments:
                        pass
                    print(f"Model loaded and verified on CPU.")
                except Exception as e2:
                    print(f"CPU fallback also failed: {e2}")
                    self.model = None

    def transcribe(self, audio_data):
        """
        audio_data: numpy array of float32
        """
        if self.model is None:
            print("[ERROR] Model not loaded!")
            return ""

        print(f"[DEBUG] Starting transcription on {len(audio_data)} samples...")
        try:
            # faster-whisper expects float32
            segments, info = self.model.transcribe(audio_data, beam_size=5, language=self.language)
            
            print(f"[DEBUG] Model detected language '{info.language}' with probability {info.language_probability}")

            full_text = ""
            segment_count = 0
            for segment in segments:
                print(f"[DEBUG] Segment found: {segment.text}")
                full_text += segment.text
                segment_count += 1
            
            print(f"[DEBUG] Transcription finished. Segments: {segment_count}. Text: {full_text}")
            return full_text.strip()
        except Exception as e:
            print(f"[ERROR] Logic Error in Transcribe: {e}")
            import traceback
            traceback.print_exc()
            return ""
