
import customtkinter as ctk
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
    def __init__(self, status_callback_ref):
        super().__init__()

        self.status_callback_ref = status_callback_ref

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

        self.canvas.bind("<Button-1>", self.start_move)
        self.canvas.bind("<B1-Motion>", self.do_move)

        # Deferred re-center to ensure correct positioning after window is mapped
        self.after(100, self.update_geometry)

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
        try:
            rect = RECT()
            windll.user32.SystemParametersInfoW(48, 0, byref(rect), 0)
            return rect.left, rect.top, rect.right, rect.bottom
        except:
            return 0, 0, self.winfo_screenwidth(), self.winfo_screenheight()

    def update_geometry(self):
        try:
            left, top, right, bottom = self.get_work_area()
            screen_w = right - left
            x = left + (screen_w - self.width) // 2
            # Use ACTIVE_HEIGHT as baseline so expanding doesn't overlap taskbar
            y = bottom - self.ACTIVE_HEIGHT - 10 + (self.ACTIVE_HEIGHT - self.height) // 2
            self.geometry(f"{self.width}x{self.height}+{int(x)}+{int(y)}")
            self.canvas.configure(width=self.width, height=self.height)
        except Exception as e:
            print(f"[ERR] Geometry: {e}")

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

    # ─── Drag ────────────────────────────────────────────────────────────
    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def do_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.winfo_x() + deltax
        y = self.winfo_y() + deltay
        self.geometry(f"+{x}+{y}")

    # ─── Status / Quit ───────────────────────────────────────────────────
    def set_status(self, text, color="white"):
        pass

    def quit_app(self):
        self.quit()
