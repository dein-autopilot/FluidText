
import sounddevice as sd
import numpy as np

class AudioCapture:
    def __init__(self, sample_rate=16000):
        self.sample_rate = sample_rate
        self.recording = []
        self.stream = None
        self.is_recording = False

    def start_recording(self):
        self.recording = []
        self.is_recording = True
        # sounddevice provides a simple way to record
        self.stream = sd.InputStream(samplerate=self.sample_rate, channels=1, callback=self.audio_callback)
        self.stream.start()

    def audio_callback(self, indata, frames, time, status):
        if status:
            print(f"[WARN] Audio Status: {status}")
        if self.is_recording:
            # print(f".", end="", flush=True) # Simple alive check
            self.recording.append(indata.copy())

    def get_last_amplitude(self):
        """Returns the RMS amplitude of the last recorded chunk (normalized 0-1 range approx)"""
        if not self.recording:
            return 0.0
        
        try:
            # Look at the last chunk
            last_chunk = self.recording[-1]
            # Simple RMS
            rms = np.sqrt(np.mean(last_chunk**2))
            
            # Boost significantly - typical mic input is very quiet
            # 15x multiplier should make normal speech reach 0.3-0.7 range
            normalized = min(rms * 15, 1.0)
            return normalized
        except:
            return 0.0

    def stop_recording(self):
        self.is_recording = False
        print(f"[DEBUG] Stop recording called. Chunks recorded: {len(self.recording)}")
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        
        if not self.recording:
            print("[WARN] No recording data found!")
            return None
            
        # Concatenate all chunks
        audio_data = np.concatenate(self.recording, axis=0)
        
        # Flatten and ensure float32
        return audio_data.flatten().astype(np.float32)
