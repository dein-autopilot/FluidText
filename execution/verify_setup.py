
import sounddevice as sd
import ctranslate2
from faster_whisper import WhisperModel

print("--- Hardware Verification ---")

# Check CTranslate2 CUDA
cuda_count = ctranslate2.get_cuda_device_count()
print(f"CTranslate2 CUDA Support: {cuda_count > 0}")
if cuda_count > 0:
    print(f"Device count: {cuda_count}")
else:
    print("WARNING: CTranslate2 did not find CUDA devices. Will fall back to CPU.")

# Check Audio Devices
print("\n--- Audio Devices ---")
try:
    print(sd.query_devices())
except Exception as e:
    print(f"Error querying audio devices: {e}")

print("\n--- Model Check ---")
try:
    print("Attempting to load a tiny model to verify libraries...")
    # Use tiny model for quick verification, confirm it downloads and loads
    model = WhisperModel("tiny", device="cuda" if cuda_count > 0 else "cpu", compute_type="int8")
    print("Model loaded successfully!")
except Exception as e:
    print(f"Error loading model: {e}")

print("---------------------")
