
import customtkinter as ctk
import tkinter as tk
import math
import random
import os
import ctypes
from ctypes import windll, Structure, c_long, byref

class RECT(Structure):
    _fields_ = [
        ("left", c_long),
        ("top", c_long),
        ("right", c_long),
        ("bottom", c_long),
    ]

class Overlay(ctk.CTk):
    def __init__(self, controller=None):
        super().__init__()

        # The controller lets the pill's right-click menu reach app actions
        # (open settings, quit). It may be None in standalone/dev use.
        self.controller = controller

        # ── Dimensions (snug pill, minimal padding) ──
        self.IDLE_WIDTH = 96
        self.IDLE_HEIGHT = 28
        self.ACTIVE_WIDTH = 140
        self.ACTIVE_HEIGHT = 34

        # ── Colors ──
        self.COLOR_BG = "#1a1a22"
        self.COLOR_BORDER = "#3a3a48"
        self.COLOR_ACCENT = "#7ec87e"
        self.COLOR_TEXT = "#c8c8d0"
        self.COLOR_WAVE = "#8fbfb8"
        self.TRANSPARENT_KEY = "#f0f0f0"

        # ── State ──
        self.is_active = False
        self.width = self.IDLE_WIDTH
        self.height = self.IDLE_HEIGHT
        self._anim_id = None
        self._anim_target_w = self.width
        self._anim_target_h = self.height
        self._animating = False

        # ── Waveform state (persistent bar items to avoid flicker) ──
        self._bar_ids = []
        self._num_bars = 15
        self._prev_heights = [0.0] * self._num_bars  # For smoothing

        # Swallow benign Tcl errors from pending 'after' callbacks that fire
        # while/after the window is being torn down (e.g. when switching to the
        # dashboard from the tray). They are harmless but noisy in the console.
        # These surface as Tcl *background* errors, so we override bgerror (a
        # Python report_callback_exception does not catch them).
        self.report_callback_exception = self._silence_teardown_errors
        try:
            self.tk.createcommand("bgerror", self._tcl_bgerror)
        except Exception:
            pass

        # ── Window setup ──
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.95)
        self.configure(fg_color=self.TRANSPARENT_KEY)
        self.wm_attributes("-transparentcolor", self.TRANSPARENT_KEY)

        # Hide from taskbar
        try:
            GWL_EXSTYLE = -20
            WS_EX_APPWINDOW = 0x00040000
            WS_EX_TOOLWINDOW = 0x00000080
            hwnd = windll.user32.GetParent(self.winfo_id())
            style = windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style = style & ~WS_EX_APPWINDOW | WS_EX_TOOLWINDOW
            windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        except Exception as e:
            print(f"[WARN] Taskbar hide failed: {e}")

        # Audio
        assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
        if getattr(__import__('sys'), 'frozen', False):
            assets_dir = os.path.join(__import__('sys')._MEIPASS, "assets")
        self.click_sound = os.path.join(assets_dir, "click.wav")

        # Canvas
        self.canvas = ctk.CTkCanvas(self, width=self.width, height=self.height,
                                    bg=self.TRANSPARENT_KEY, highlightthickness=0)
        self.canvas.pack()

        self.update_idletasks()
        self.update_geometry()
        self.draw_idle()

        # The pill stays anchored (centered, just above the taskbar) — it is
        # intentionally not draggable, so it can't drift and won't fight the
        # re-centering that happens while the waveform animates.
        # Right-click the pill for settings / hide / quit.
        self.canvas.bind("<Button-3>", self._open_menu)

        # Context menu (built once, reused).
        self._menu = tk.Menu(self, tearoff=0)
        self._menu.add_command(label="Einstellungen", command=self._menu_settings)
        self._menu.add_command(label="Overlay ausblenden", command=self._menu_hide)
        self._menu.add_separator()
        self._menu.add_command(label="Beenden", command=self._menu_quit)

        # Deferred re-center to ensure correct positioning after window is mapped
        self.after(100, self.update_geometry)

    # ─── Show / context menu ─────────────────────────────────────────────
    def show_overlay(self):
        """Reveal and recenter the pill (used after a tray-only start).

        A plain deiconify on an overrideredirect window doesn't always restore
        it on Windows, so we re-assert overrideredirect/topmost to force a clean
        re-map, then recenter and lift."""
        try:
            self.deiconify()
            self.overrideredirect(True)
            self.attributes("-topmost", True)
            self.attributes("-alpha", 0.95)
            self.update_geometry()
            self.lift()
        except Exception:
            pass

    def _open_menu(self, event):
        try:
            self._menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._menu.grab_release()

    def _menu_settings(self):
        if self.controller is not None:
            self.controller.open_settings()

    def _menu_hide(self):
        # Unpin via the controller so it stays hidden until explicitly shown.
        if self.controller is not None:
            self.controller._overlay_pinned = False
        try:
            self.withdraw()
        except Exception:
            pass

    def _menu_quit(self):
        if self.controller is not None:
            self.controller.quit_app()
        else:
            self.quit()

    def _silence_teardown_errors(self, exc, val, tb):
        msg = str(val)
        if "invalid command name" in msg or "application has been destroyed" in msg:
            return  # benign: a queued 'after' fired during teardown
        import traceback as _tb
        _tb.print_exception(exc, val, tb)

    def _tcl_bgerror(self, msg):
        # Tcl background error handler. Ignore the harmless teardown noise;
        # forward anything else to stderr so real errors stay visible.
        if "invalid command name" in str(msg) or "application has been destroyed" in str(msg):
            return ""
        import sys as _sys
        _sys.stderr.write(f"[Tcl] {msg}\n")
        return ""

    # ─── Pill shape ──────────────────────────────────────────────────────
    def draw_pill(self, x1, y1, x2, y2, fill, outline, width=1, tags=""):
        h = y2 - y1
        r = h / 2
        t = tags
        self.canvas.create_arc(x1, y1, x1 + h, y2,
                               start=90, extent=180,
                               fill=fill, outline=outline, width=width, style="pieslice", tags=t)
        self.canvas.create_arc(x2 - h, y1, x2, y2,
                               start=-90, extent=180,
                               fill=fill, outline=outline, width=width, style="pieslice", tags=t)
        self.canvas.create_rectangle(x1 + r - 1, y1, x2 - r + 1, y2,
                                     fill=fill, outline=fill, width=0, tags=t)
        if width > 0:
            self.canvas.create_line(x1 + r, y1, x2 - r, y1, fill=outline, width=width, tags=t)
            self.canvas.create_line(x1 + r, y2, x2 - r, y2, fill=outline, width=width, tags=t)

    # ─── Work area ───────────────────────────────────────────────────────
    def get_work_area(self):
        """Primary-monitor work area (excludes the taskbar) in *physical* pixels
        — the same coordinate space ``geometry()`` positions into on Windows."""
        try:
            rect = RECT()
            windll.user32.SystemParametersInfoW(48, 0, byref(rect), 0)
            return rect.left, rect.top, rect.right, rect.bottom
        except Exception:
            # Physical full-screen fallback (NOT winfo_*, which is logical and
            # would mismatch the physical geometry coordinate space).
            try:
                return 0, 0, windll.user32.GetSystemMetrics(0), windll.user32.GetSystemMetrics(1)
            except Exception:
                return 0, 0, self.winfo_screenwidth(), self.winfo_screenheight()

    def update_geometry(self):
        try:
            # Anchor the pill: horizontally centered, bottom edge a few px above
            # the taskbar — regardless of DPI scaling.
            #
            # Hard-won fact (verified with GetWindowRect): on Windows, Tk's
            # `geometry()` positions windows in PHYSICAL pixels, and the Win32
            # work area is also physical — so they line up directly with NO
            # conversion. (winfo_screenwidth/height report *logical* pixels and
            # must NOT be used here; mixing them in put the pill at ~3/4 height,
            # off-centre.) CustomTkinter inflates the rendered window by the DPI
            # factor, so the on-screen size is `size * scaling` physical px; we
            # use that to place the bottom/centre exactly.
            scaling = 1.0
            try:
                hwnd = windll.user32.GetParent(self.winfo_id())
                dpi = windll.user32.GetDpiForWindow(hwnd)
                if dpi:
                    scaling = dpi / 96.0
            except Exception:
                pass
            win_w = self.width * scaling
            win_h = self.height * scaling

            wl, wt, wr, wb = self.get_work_area()  # physical, taskbar-excluded
            x = wl + ((wr - wl) - win_w) / 2
            y = wb - win_h - 6  # snug above the taskbar
            self.geometry(f"{self.width}x{self.height}+{int(round(x))}+{int(round(y))}")
            self.canvas.configure(width=self.width, height=self.height)
        except Exception as e:
            print(f"[ERR] Geometry: {e}")
            # Last-resort: simple logical centering near the bottom.
            try:
                screen_w = self.winfo_screenwidth()
                screen_h = self.winfo_screenheight()
                x = (screen_w - self.width) // 2
                y = screen_h - self.height - 48
                self.geometry(f"{self.width}x{self.height}+{int(x)}+{int(y)}")
            except Exception:
                pass

    # ─── State switch ────────────────────────────────────────────────────
    def set_state(self, active=True):
        if self.is_active == active:
            return
        self.is_active = active

        if self.is_active:
            self._anim_target_w = self.ACTIVE_WIDTH
            self._anim_target_h = self.ACTIVE_HEIGHT
            self.play_sound(self.click_sound, volume_scale=0.15)
        else:
            self._anim_target_w = self.IDLE_WIDTH
            self._anim_target_h = self.IDLE_HEIGHT
            self._bar_ids = []  # Reset bar references
            self._prev_heights = [0.0] * self._num_bars
            self.play_sound(self.click_sound, volume_scale=0.1)

        self._animate_resize()

    def _animate_resize(self):
        if self._anim_id:
            self.after_cancel(self._anim_id)
            self._anim_id = None

        self._animating = True

        dw = self._anim_target_w - self.width
        dh = self._anim_target_h - self.height

        if abs(dw) <= 4 and abs(dh) <= 4:
            self.width = self._anim_target_w
            self.height = self._anim_target_h
            self.update_geometry()
            self._animating = False
            if self.is_active:
                self.draw_active_base()
            else:
                self.draw_idle()
            return

        self.width = int(self.width + dw * 0.3)
        self.height = int(self.height + dh * 0.3)
        self.update_geometry()

        self.canvas.delete("all")
        self._bar_ids = []
        self.draw_pill(0, 0, self.width, self.height,
                       fill=self.COLOR_BG, outline=self.COLOR_BORDER)

        self._anim_id = self.after(16, self._animate_resize)

    # ─── Sound ───────────────────────────────────────────────────────────
    def play_sound(self, file_path, volume_scale=1.0):
        if os.path.exists(file_path):
            try:
                import winsound
                winsound.PlaySound(file_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except:
                pass

    # ─── Idle ────────────────────────────────────────────────────────────
    def draw_idle(self):
        self.canvas.delete("all")
        self._bar_ids = []
        self.draw_pill(0, 0, self.width, self.height,
                       fill=self.COLOR_BG, outline=self.COLOR_BORDER)

        cx, cy = self.width / 2, self.height / 2

        # Green dot – tight to left
        dr = 3
        dx = cx - 18
        self.canvas.create_oval(dx - dr, cy - dr, dx + dr, cy + dr,
                                fill=self.COLOR_ACCENT, outline="")

        # "READY" text – tight next to dot
        self.canvas.create_text(cx + 7, cy + 1, text="READY",
                                fill=self.COLOR_TEXT,
                                font=("Segoe UI Semibold", 7, "bold"),
                                anchor="center")

    # ─── Active ──────────────────────────────────────────────────────────
    def draw_active_base(self):
        self.canvas.delete("all")
        self._bar_ids = []
        self.draw_pill(0, 0, self.width, self.height,
                       fill=self.COLOR_BG, outline=self.COLOR_BORDER)

    # ─── Waveform (flicker-free using coords update) ─────────────────────
    def update_visualizer(self, volume):
        if not self.is_active or self._animating:
            return

        vol = min(max(volume * 5.0, 0.15), 1.0)  # Much higher gain
        cx, cy = self.width / 2, self.height / 2

        num_bars = self._num_bars
        bar_w = 1.5          # Thin lines
        bar_gap = 2.5
        max_h = self.height * 0.72  # Use more of the available height

        total_w = (num_bars * bar_w) + ((num_bars - 1) * bar_gap)
        start_x = cx - total_w / 2

        # Create bars on first call, then reuse via coords()
        if not self._bar_ids or len(self._bar_ids) != num_bars:
            self.canvas.delete("wave")
            self._bar_ids = []
            for i in range(num_bars):
                x = start_x + i * (bar_w + bar_gap)
                bid = self.canvas.create_line(
                    x, cy, x, cy,
                    fill=self.COLOR_WAVE, width=bar_w, capstyle="round", tags="wave"
                )
                self._bar_ids.append(bid)

        # Update bar positions (no delete/recreate = no flicker)
        for i in range(num_bars):
            dist = abs(i - (num_bars - 1) / 2.0)
            max_dist = (num_bars - 1) / 2.0
            scale = 1.0 - (dist / max_dist) * 0.55
            scale = max(scale, 0.25)

            target_h = vol * max_h * scale * random.uniform(0.75, 1.15)
            target_h = max(1.5, target_h)

            # Smooth: lerp from previous height to reduce jitter
            prev = self._prev_heights[i]
            h = prev + (target_h - prev) * 0.4
            self._prev_heights[i] = h

            x = start_x + i * (bar_w + bar_gap)
            self.canvas.coords(self._bar_ids[i], x, cy - h / 2, x, cy + h / 2)

    # ─── Status / Quit ───────────────────────────────────────────────────
    def set_status(self, text, color="white"):
        pass

    def quit_app(self):
        self.quit()
