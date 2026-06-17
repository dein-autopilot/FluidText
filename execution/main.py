
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

        # Self-heal autostart: if it's enabled, make sure the registry points at
        # the executable's *current* location (it may have been moved/renamed).
        try:
            from platform_support import get_autostart
            getattr(get_autostart(), "refresh", lambda: None)()
        except Exception as e:
            print(f"[WARN] Autostart refresh skipped: {e}")

        # Load logic components
        self.transcriber = None
        self.audio = AudioCapture()
        self.injector = TextInjector()

        self.is_recording = False
        self.hotkey = normalize_hotkey(self.settings.get("hotkey"))
        self.hotkey2 = normalize_hotkey(self.settings.get("hotkey2"))
        self.hotkey_monitor = None

        # The overlay pill is one of the two windows the driver loop shows. We
        # keep a dedicated reference (separate from self.app) so the background
        # listener can update it only when it actually exists and is an Overlay.
        self.overlay = None
        # When "pinned" the pill stays visible while idle (normal launch / tray
        # "Show Overlay"). When not pinned (autostart / minimize-to-tray) it only
        # appears while you are speaking, then hides again — discreet but visible.
        self._overlay_pinned = False
        self._listener_running = False

        # Start the global push-to-talk listener up front. Decoupling it from the
        # GUI mainloop means dictation works no matter which window is on screen —
        # including while the settings window is open.
        self._start_hotkey_listener()

        # Driver loop: we switch between the dashboard and the overlay by queueing
        # the next view and letting the current mainloop exit — never by nesting
        # mainloops. Nesting (the old approach) made the tray "Settings"/"Restart"
        # actions hang or fail, so you couldn't reopen the dashboard once running.
        self._next_action = "overlay" if autostart else "dashboard"
        self._pending_hidden = autostart
        self._reload_model = True  # load on first overlay; reused on plain re-show
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

    # ─── Global push-to-talk listener ────────────────────────────────────
    # Runs in its own daemon thread, independent of any GUI window, so holding
    # the hotkey records and types text whether the overlay, the settings
    # window, or nothing at all is currently shown.
    def _start_hotkey_listener(self):
        if self._listener_running:
            return
        if not self.hotkey_monitor:
            self.hotkey_monitor = get_hotkey_monitor()
        self._listener_running = True
        threading.Thread(target=self._hotkey_loop, daemon=True).start()

    def _hotkey_loop(self):
        while self._listener_running:
            try:
                pressed = False
                for hk in (self.hotkey, self.hotkey2):
                    if hk and self.hotkey_monitor.is_pressed(hk):
                        pressed = True
                        break
            except Exception as e:
                if not getattr(self, '_logged_hotkey_error', False):
                    try:
                        with open(log_path("debug_hotkey_error.txt"), "w") as f:
                            f.write(f"Error checking hotkey '{self.hotkey}'/'{self.hotkey2}': {e}")
                    except Exception:
                        pass
                    self._logged_hotkey_error = True
                pressed = False

            if pressed and not self.is_recording:
                self.start_recording()
            elif not pressed and self.is_recording:
                self.stop_recording_and_transcribe()

            time.sleep(0.02)

    # ─── Overlay UI marshaling ───────────────────────────────────────────
    # The listener and transcription run off-thread; any overlay update must be
    # bounced onto the Tk thread via after(). These are no-ops when the overlay
    # isn't the current window (e.g. while the settings window is open).
    def _ui(self, fn, delay=0):
        ov = self.overlay
        if not ov:
            return
        try:
            ov.after(delay, lambda: self._safe_ui(ov, fn))
        except Exception:
            pass

    def _safe_ui(self, ov, fn):
        if ov is not self.overlay:
            return
        try:
            fn(ov)
        except Exception:
            pass

    def _set_overlay_visible(self, visible):
        def _apply(ov):
            if visible:
                ov.show_overlay()
            else:
                ov.withdraw()
        self._ui(_apply)

    def _run_dashboard(self):
        # No overlay while the settings window owns the screen.
        self.overlay = None
        self.app = ModernDashboard(on_start_callback=self._on_dashboard_start)
        # Poll for a tray "Show Overlay" request so it works even from here.
        self.app.after(150, self._dashboard_poll)
        self.app.mainloop()

    def _dashboard_poll(self):
        if getattr(self, 'request_restart', False):
            self.request_restart = False
            self._next_action = "overlay"
            self._pending_hidden = False
            try:
                self.app.destroy()
            except Exception:
                pass
            return

        # Tray "Einstellungen" while the dashboard is already open: just bring it
        # to the front (it may be minimized or behind other windows).
        if getattr(self, 'request_dashboard_front', False):
            self.request_dashboard_front = False
            try:
                self.app.deiconify()
                self.app.lift()
                self.app.focus_force()
                self.app.attributes("-topmost", True)
                self.app.after(300, lambda: self.app.attributes("-topmost", False))
            except Exception:
                pass

        try:
            self.app.after(150, self._dashboard_poll)
        except Exception:
            pass

    def _on_dashboard_start(self, hidden=False):
        # The dashboard destroys itself, then calls this. Queue the overlay; the
        # driver loop shows it once the dashboard's mainloop has fully exited.
        self._pending_hidden = hidden
        self._reload_model = True  # settings (model/language/vocab) may have changed
        self._next_action = "overlay"

    def _run_overlay(self, hidden=False):
        try:
            # Reload settings just in case (hotkeys may have changed in settings)
            self.settings.load_settings()
            self.hotkey = normalize_hotkey(self.settings.get("hotkey"))
            self.hotkey2 = normalize_hotkey(self.settings.get("hotkey2"))
            self._hotkey_check_counter = 0  # Counter for periodic hotkey reload

            # Platform hotkey monitor (Windows: keyboard, macOS: pynput listener)
            if not self.hotkey_monitor:
                self.hotkey_monitor = get_hotkey_monitor()

            model_size = self.settings.get("model_size")
            self._language = self.settings.get("language")

            # Init Overlay (pass controller so the pill's right-click menu can
            # open settings / quit, and so it can recenter itself on demand).
            self.app = Overlay(controller=self)
            self.overlay = self.app

            # Hidden (autostart / minimize-to-tray): only the tray icon for now.
            # The pill then appears just while you speak. A normal launch or a
            # tray "Show Overlay" pins it so it stays visible.
            self._overlay_pinned = not hidden
            if hidden:
                self.app.withdraw()

            # Protocol handler for closing
            try:
                self.app.protocol("WM_DELETE_WINDOW", self.quit_app)
            except:
                pass

            # Load the model only when needed — on first launch, or after the
            # settings changed. A plain re-show from the tray reuses it (fast).
            need_load = (self._reload_model or self.transcriber is None
                         or self.transcriber.model is None)
            self._reload_model = False
            if need_load:
                self.app.set_status("Loading Model...", "orange")
                threading.Thread(target=self.init_transcriber, args=(model_size,), daemon=True).start()
            else:
                self.app.set_status("Ready", "white")

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
        # "Settings" is the default action (fires on double-click / left click).
        # The pill auto-shows while you speak, so the only thing the tray needs
        # to offer is a reliable way back into the settings window.
        menu = pystray.Menu(
            pystray.MenuItem("Settings", self.open_settings_from_tray, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self.quit_app)
        )
        self.tray_icon = pystray.Icon("FluidText", image, "FluidText AI", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def open_settings_from_tray(self, icon=None, item=None):
        # Runs on the pystray thread → must NOT touch Tk directly. We only raise
        # a flag; the GUI-thread loops (which are alive — they drive the pill's
        # waveform) tear down the current view and show the settings window.
        if self.overlay is not None:
            # Overlay view: the overlay tick switches to the dashboard.
            self._reload_model = False  # reuse the loaded model — fast switch
            self.request_dashboard = True
        else:
            # Already in dashboard view: bring it to the front (it may be behind
            # other windows). Handled by the dashboard poller.
            self.request_dashboard_front = True

    def open_settings(self):
        # Invoked by the overlay pill's right-click menu. The overlay GUI tick
        # picks this up, tears down the pill, and shows the settings window.
        self.request_dashboard = True

    def quit_app(self, icon=None, item=None):
        self._listener_running = False
        try:
            if self.tray_icon:
                self.tray_icon.stop()
        except Exception:
            pass
        if self.app:
            try:
                self.app.quit()
            except Exception:
                pass
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
        # GUI-thread tick that runs while the overlay is the active window. The
        # hotkey/recording logic now lives in the background listener; this loop
        # only handles view switches (from the tray/pill menu) and the pill's
        # waveform animation — both of which must run on the Tk thread.
        if getattr(self, 'request_dashboard', False):
            self.request_dashboard = False
            self._next_action = "dashboard"
            self.overlay = None
            self.app.destroy()
            return

        if getattr(self, 'request_restart', False):
            self.request_restart = False
            self._next_action = "overlay"
            self._pending_hidden = False
            self.overlay = None
            self.app.destroy()
            return

        # Periodically reload hotkeys from settings (every ~2 seconds).
        self._hotkey_check_counter = getattr(self, '_hotkey_check_counter', 0) + 1
        if self._hotkey_check_counter >= 40:
            self._hotkey_check_counter = 0
            try:
                self.settings.load_settings()
                for attr, key in (("hotkey", "hotkey"), ("hotkey2", "hotkey2")):
                    new_hk = normalize_hotkey(self.settings.get(key))
                    if new_hk != getattr(self, attr):
                        print(f"[INFO] {key} changed: {getattr(self, attr)} -> {new_hk}")
                        setattr(self, attr, new_hk)
                        self._logged_hotkey_error = False
            except Exception:
                pass

        # Visualizer Update (driven by the recording state the listener sets).
        # Guarded so a transient draw error can never kill the loop — if it did,
        # the tray "Show Overlay" / view-switch flags above would stop being
        # serviced (which is exactly how those actions used to "do nothing").
        try:
            if self.is_recording and hasattr(self.audio, 'get_last_amplitude'):
                self.app.update_visualizer(self.audio.get_last_amplitude())
            else:
                self.app.update_visualizer(0)
        except Exception:
            pass

        try:
            self.app.after(50, self.update_visualizer_loop)
        except Exception:
            pass

    def start_recording(self):
        # Called from the background listener thread.
        if self.transcriber is None or self.transcriber.model is None:
            return  # Model not loaded yet — nothing to transcribe into.

        self.is_recording = True
        self.audio.start_recording()
        # Reveal the pill (even after a tray-only autostart) and keep it up from
        # now on — pinning here avoids flaky withdraw/deiconify churn on every
        # dictation while still honouring a discreet, tray-only boot.
        self._overlay_pinned = True
        self._set_overlay_visible(True)
        self._ui(lambda ov: ov.set_state(True))  # Force Active State

    def stop_recording_and_transcribe(self):
        # Called from the background listener thread.
        self.is_recording = False
        self._ui(lambda ov: ov.set_state(False))  # Force Idle State

        audio_data = self.audio.stop_recording()

        # Threaded transcribe
        threading.Thread(target=self.process_audio, args=(audio_data,), daemon=True).start()

    def process_audio(self, audio_data):
        try:
            if audio_data is None or len(audio_data) == 0:
                return
            if self.transcriber:
                text = self.transcriber.transcribe(audio_data)
                if text:
                    self.injector.type_text(text)
        except Exception as e:
            print(f"[ERROR] Inference: {e}")

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
