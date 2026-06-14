
import customtkinter as ctk
import threading
import time
import sys
import os
import numpy as np

# Set AppUserModelID to ensure taskbar icon is correct
try:
    from ctypes import windll
    windll.shell32.SetCurrentProcessExplicitAppUserModelID("FluidText.AI.App.1.0")
except ImportError:
    pass

# Ensure we can find our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def log_path(filename):
    """Return a writable path for crash/debug logs. The current working
    directory is unreliable on autostart (Windows may launch us from
    system32), so we always write into the per-user data directory."""
    try:
        import appdirs
        log_dir = os.path.join(appdirs.user_data_dir("FluidText", "FluidTextAI"), "logs")
        os.makedirs(log_dir, exist_ok=True)
        return os.path.join(log_dir, filename)
    except Exception:
        return filename

from transcriber import Transcriber
from audio_capture import AudioCapture
from injector import TextInjector
from settings_manager import SettingsManager
from gui_dashboard import ModernDashboard
from gui_overlay import Overlay
from utils import normalize_hotkey
from platform_support import get_hotkey_monitor

import pystray
from PIL import Image, ImageDraw

def create_icon_image():
    """Create a teal-gradient tray icon matching the FluidText brand"""
    # Try to load pre-generated icon first
    if getattr(sys, 'frozen', False):
        assets_dir = os.path.join(sys._MEIPASS, "assets")
    else:
        assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
    icon_path = os.path.join(assets_dir, "tray_icon.png")
    if os.path.exists(icon_path):
        return Image.open(icon_path)
    
    # Fallback: generate programmatically with teal-green-to-blue gradient
    size = 64
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    dc = ImageDraw.Draw(image)
    
    # Background: Teal gradient circle
    center = size // 2
    for r in range(center, 0, -1):
        t = 1 - (r / center)
        if t < 0.5:
            # Dark teal to mint-green
            t2 = t * 2
            red = int(45 + t2 * 77)    # 45 -> 122
            green = int(95 + t2 * 89)   # 95 -> 184
            blue = int(93 + t2 * 45)    # 93 -> 138
        else:
            # Mint-green to blue
            t2 = (t - 0.5) * 2
            red = int(122 - t2 * 32)    # 122 -> 90
            green = int(184 - t2 * 30)  # 184 -> 154
            blue = int(138 + t2 * 70)   # 138 -> 208
        
        dc.ellipse([center - r, center - r, center + r, center + r], 
                  fill=(red, green, blue, 255))
    
    # Microphone shape (simplified, modern)
    mic_color = (255, 255, 255, 255)
    
    # Mic body
    dc.ellipse([22, 14, 42, 28], fill=mic_color)
    dc.rectangle([22, 20, 42, 38], fill=mic_color)
    dc.ellipse([22, 32, 42, 44], fill=mic_color)
    
    # Stand/base
    dc.rectangle([30, 44, 34, 50], fill=mic_color)
    dc.rectangle([24, 48, 40, 52], fill=mic_color)
    
    return image

class ApplicationController:
    def __init__(self, autostart=False):
        self.settings = SettingsManager()
        self.app = None
        self.tray_icon = None
        self.autostart = autostart

        # Load logic components
        self.transcriber = None
        self.audio = AudioCapture()
        self.injector = TextInjector()

        self.is_recording = False
        self.hotkey = self.settings.get("hotkey")
        self.hotkey_monitor = None

        # Driver loop: we switch between the dashboard and the overlay by queueing
        # the next view and letting the current mainloop exit — never by nesting
        # mainloops. Nesting (the old approach) made the tray "Settings"/"Restart"
        # actions hang or fail, so you couldn't reopen the dashboard once running.
        self._next_action = "overlay" if autostart else "dashboard"
        self._pending_hidden = autostart
        self.run()

    def run(self):
        while self._next_action:
            action = self._next_action
            self._next_action = None
            if action == "dashboard":
                self._run_dashboard()
            elif action == "overlay":
                hidden = self._pending_hidden
                self._pending_hidden = False
                self._run_overlay(hidden=hidden)

    def _run_dashboard(self):
        self.app = ModernDashboard(on_start_callback=self._on_dashboard_start)
        self.app.mainloop()

    def _on_dashboard_start(self, hidden=False):
        # The dashboard destroys itself, then calls this. Queue the overlay; the
        # driver loop shows it once the dashboard's mainloop has fully exited.
        self._pending_hidden = hidden
        self._next_action = "overlay"

    def _run_overlay(self, hidden=False):
        try:
            # Reload settings just in case
            self.settings.load_settings()
            self.hotkey = normalize_hotkey(self.settings.get("hotkey"))
            self._hotkey_check_counter = 0  # Counter for periodic hotkey reload

            # Platform hotkey monitor (Windows: keyboard, macOS: pynput listener)
            if not self.hotkey_monitor:
                self.hotkey_monitor = get_hotkey_monitor()

            model_size = self.settings.get("model_size")
            self._language = self.settings.get("language")

            # Init Overlay
            self.app = Overlay(status_callback_ref=None)

            # Hidden (autostart / minimize-to-tray): only show the tray icon
            if hidden:
                self.app.withdraw()

            # Protocol handler for closing
            try:
                self.app.protocol("WM_DELETE_WINDOW", self.quit_app)
            except:
                pass

            # Start Model Loading
            self.app.set_status("Loading Model...", "orange")
            threading.Thread(target=self.init_transcriber, args=(model_size,), daemon=True).start()

            print(f"[INFO] Using hotkey: {self.hotkey}")

            # Start Visualizer Loop
            self.update_visualizer_loop()

            # Start Tray Icon (once; it persists across dashboard/overlay switches)
            if not self.tray_icon:
                self.setup_tray_icon()

            self.app.mainloop()
        except Exception as e:
            with open(log_path("launch_crash.txt"), "w") as f:
                import traceback
                f.write(traceback.format_exc())
            try:
                import tkinter.messagebox
                tkinter.messagebox.showerror("Launch Error", f"App crashed during launch:\n{e}\nSee launch_crash.txt")
            except:
                pass
            self._next_action = None  # stop the driver loop on a genuine failure

    def setup_tray_icon(self):
        image = create_icon_image()
        menu = pystray.Menu(
            pystray.MenuItem("Show Overlay", self.show_overlay_from_tray),
            pystray.MenuItem("Settings", self.open_settings_from_tray),
            pystray.MenuItem("Restart Overlay", self.restart_overlay_from_tray),
            pystray.MenuItem("Quit", self.quit_app)
        )
        self.tray_icon = pystray.Icon("FluidText", image, "FluidText AI", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def show_overlay_from_tray(self, icon, item):
        if self.app:
            self.app.after(0, self.app.deiconify)

    def open_settings_from_tray(self, icon, item):
        self.request_dashboard = True

    def restart_overlay_from_tray(self, icon, item):
        self.request_restart = True

    def quit_app(self, icon, item):
        self.tray_icon.stop()
        if self.app:
            self.app.quit()
        os._exit(0)

    def init_transcriber(self, model_size):
        language = getattr(self, '_language', 'de')
        vocabulary = self.settings.get("vocabulary")
        replacements = self.settings.get("replacements")
        self.transcriber = Transcriber(
            model_size=model_size, device="cuda", language=language,
            vocabulary=vocabulary, replacements=replacements,
        )
        self.transcriber.load_model()
        # The user may have switched windows while the model loaded; set_status
        # only exists on the overlay, so guard against a stale/other window.
        try:
            self.app.set_status("Ready", "white")
        except Exception:
            pass

    def update_visualizer_loop(self):
        # Check for tray requests. We only queue the next view and destroy the
        # current window; the driver loop (run) then shows it — no nested mainloop.
        if getattr(self, 'request_dashboard', False):
            self.request_dashboard = False
            self._next_action = "dashboard"
            self.app.destroy()
            return

        if getattr(self, 'request_restart', False):
            self.request_restart = False
            self._next_action = "overlay"
            self._pending_hidden = False
            self.app.destroy()
            return

        # Periodically reload hotkey from settings (every ~2 seconds = 40 iterations * 50ms)
        self._hotkey_check_counter = getattr(self, '_hotkey_check_counter', 0) + 1
        if self._hotkey_check_counter >= 40:
            self._hotkey_check_counter = 0
            try:
                self.settings.load_settings()
                new_hotkey = normalize_hotkey(self.settings.get("hotkey"))
                if new_hotkey and new_hotkey != self.hotkey:
                    print(f"[INFO] Hotkey changed: {self.hotkey} -> {new_hotkey}")
                    self.hotkey = new_hotkey
                    self._logged_hotkey_error = False  # Reset error flag for new hotkey
            except:
                pass

        # Check hotkey state
        try:
            is_pressed = self.hotkey_monitor.is_pressed(self.hotkey)
        except Exception as e:
            # If checking the hotkey fails, log it once (to avoid spamming IO)
            if not getattr(self, '_logged_hotkey_error', False):
                with open(log_path("debug_hotkey_error.txt"), "w") as f:
                    f.write(f"Error checking hotkey '{self.hotkey}': {e}")
                self._logged_hotkey_error = True
            is_pressed = False

        if is_pressed:
            if not self.is_recording:
                self.start_recording()
        else:
            if self.is_recording:
                self.stop_recording_and_transcribe()
        
        # Visualizer Update
        if self.is_recording:
            try:
                if hasattr(self.audio, 'get_last_amplitude'):
                    vol = self.audio.get_last_amplitude()
                    self.app.update_visualizer(vol)
            except:
                pass
        else:
             self.app.update_visualizer(0)
             
        self.app.after(50, self.update_visualizer_loop)

    def start_recording(self):
        if self.transcriber and self.transcriber.model is None:
            return # Model not ready
            
        self.is_recording = True
        if self.app:
            self.app.set_status("Listening", "#00ff00")
            self.app.set_state(True) # Force Active State
        self.audio.start_recording()

    def stop_recording_and_transcribe(self):
        self.is_recording = False
        if self.app:
            self.app.set_status("Transcribing", "orange")
            self.app.set_state(False) # Force Idle State
        
        audio_data = self.audio.stop_recording()
        
        # Threaded transcribe
        threading.Thread(target=self.process_audio, args=(audio_data,), daemon=True).start()

    def process_audio(self, audio_data):
        if audio_data is None or len(audio_data) == 0:
            if self.app:
                self.app.after(0, lambda: self.app.set_status("Ready", "white"))
            return

        try:
            if self.transcriber:
                text = self.transcriber.transcribe(audio_data)
                if text:
                    self.injector.type_text(text)
        except Exception as e:
            print(f"[ERROR] Inference: {e}")
        
        if self.app:
            self.app.after(0, lambda: self.app.set_status("Ready", "white"))

if __name__ == "__main__":
    try:
        # Check for --autostart flag
        autostart = "--autostart" in sys.argv
        
        # Global Crash Logging
        ctk.set_appearance_mode("dark")
        controller = ApplicationController(autostart=autostart)
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        # Write to the per-user log dir (CWD may be read-only on autostart)
        with open(log_path("crash_log.txt"), "w") as f:
            f.write(f"Startup Crash Error:\n{error_msg}")
        print(error_msg)
        # Keep console open if possible
        input("Press Enter to exit...")
