import wave
import math
import struct
import os

def generate_wave(filename, duration=0.5, freq=440.0, volume=0.5, type="sine"):
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        
        for i in range(n_samples):
            t = i / sample_rate
            
            if type == "subtle_blip":
                # Ultra-subtle, smooth micro-tone
                # Gentle sine with quick fade — like a soft UI confirmation
                env = math.exp(-t * 25.0)  # Very fast fade
                
                # Smooth pure tone with tiny warm harmonic
                sample = volume * env * (
                    0.8 * math.sin(2 * math.pi * freq * t) +
                    0.2 * math.sin(2 * math.pi * freq * 1.5 * t) * math.exp(-t * 30)
                )
            
            else:
                env = math.exp(-t * 40)
                sample = volume * env * math.sin(2 * math.pi * freq * t)
            
            sample_int = int(max(-32767, min(32767, sample * 32767)))
            wav_file.writeframes(struct.pack('h', sample_int))

assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
os.makedirs(assets_dir, exist_ok=True)

# Ultra-subtle confirmation blip — barely noticeable, smooth and warm
generate_wave(os.path.join(assets_dir, "click.wav"), duration=0.08, freq=720.0, volume=0.006, type="subtle_blip")

print("Audio files generated (subtle blip version).")
