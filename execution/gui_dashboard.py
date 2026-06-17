import customtkinter as ctk
import threading
import tkinter.messagebox
import sys
import os
import glob
from PIL import Image
from settings_manager import SettingsManager
from utils import normalize_hotkey
from transcriber import check_nvidia_dlls
from platform_support import get_autostart, read_hotkey, IS_MAC
import appdirs

# ── Refined Palette – Harmonized with Logo ──────────────────────────────
COLORS = {
    "bg":           "#0a0a0e",      # Deepest dark
    "card_bg":      "#151519",      # Card / input bg
    "border":       "#2a2a30",      # Subtle border
    "border_light": "#3a3a42",      # Slightly visible border
    "accent":       "#8ea88e",      # Sage Green (Primary)
    "accent_hover": "#a2bfa2",      # Lighter Sage
    "accent_blue":  "#82c8ff",      # Blue accent (info, save)
    "text_main":    "#e8e8ec",      # Primary text
    "text_sec":     "#7a7a88",      # Dimmed text
    "text_label":   "#9090a0",      # Section labels
    "input_bg":     "#111115",      # Dropdown bg
    "success":      "#7ec87e",      # Green dot / check
    "danger":       "#e53935",
    "switch_on":    "#5b8bd4",      # Blue toggle
}

# Language display mapping
LANGUAGES = {
    "auto": "Auto-detect",
    "de": "Deutsch (de)",
    "en": "English (en)",
    "fr": "Français (fr)",
    "es": "Español (es)",
    "it": "Italiano (it)",
    "nl": "Nederlands (nl)",
    "ja": "日本語 (ja)",
    "zh": "中文 (zh)",
    "pt": "Português (pt)",
    "ru": "Русский (ru)",
    "ko": "한국어 (ko)",
    "ar": "العربية (ar)",
    "hi": "हिन्दी (hi)",
    "tr": "Türkçe (tr)",
    "pl": "Polski (pl)",
    "uk": "Українська (uk)",
    "sv": "Svenska (sv)",
    "da": "Dansk (da)",
    "no": "Norsk (no)",
    "fi": "Suomi (fi)",
    "cs": "Čeština (cs)",
    "ro": "Română (ro)",
    "hu": "Magyar (hu)",
}

# Reverse lookup: display string -> code
LANG_DISPLAY_TO_CODE = {v: k for k, v in LANGUAGES.items()}

class ModernDashboard(ctk.CTk):
    def __init__(self, on_start_callback):
        super().__init__()
        self.on_start_callback = on_start_callback
        self.settings_manager = SettingsManager()
        self._downloading = False

        # Silence benign Tcl background errors from pending 'after' callbacks
        # (e.g. customtkinter's check_dpi_scaling) that fire as the window is
        # torn down when switching views. Harmless; just noisy in the console.
        try:
            self.tk.createcommand("bgerror", self._tcl_bgerror)
        except Exception:
            pass

        # ── Assets path (works in dev and frozen/PyInstaller) ──
        if getattr(__import__('sys'), 'frozen', False):
            self.assets_dir = os.path.join(__import__('sys')._MEIPASS, "assets")
        else:
            self.assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

        # ── Set AppUserModelID so Windows shows our icon, not Python's ──
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FluidText.AI.Dashboard")
        except:
            pass

        self.title("FluidText AI")
        icon_path = os.path.join(self.assets_dir, "icon.ico")
        try:
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except:
            pass

        # ── Window Config – Frameless, modern 4:3 ──
        self.overrideredirect(True)
        # Target a 4:3 window (960x720), scaled down to fit smaller screens while
        # keeping the aspect ratio. Each column scrolls if content overflows.
        sh = self.winfo_screenheight()
        sw = self.winfo_screenwidth()
        win_h = min(720, max(560, sh - 140))
        win_w = int(win_h * 4 / 3)
        if win_w > sw - 80:               # too wide for the screen → fit to width
            win_w = sw - 80
            win_h = int(win_w * 3 / 4)
        self.win_w, self.win_h = win_w, win_h
        self.geometry(f"{win_w}x{win_h}")
        self.configure(fg_color=COLORS["bg"])

        # Center on screen
        self.update_idletasks()
        x = (sw - win_w) // 2
        y = (sh - win_h) // 2
        self.geometry(f"+{x}+{y}")

        # ── Force taskbar visibility despite overrideredirect ──
        try:
            import ctypes
            GWL_EXSTYLE = -20
            WS_EX_APPWINDOW = 0x00040000
            WS_EX_TOOLWINDOW = 0x00000080
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style = (style | WS_EX_APPWINDOW) & ~WS_EX_TOOLWINDOW
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)

            # ── Set taskbar icon via Win32 API ──
            if os.path.exists(icon_path):
                IMAGE_ICON = 1
                LR_LOADFROMFILE = 0x00000010
                LR_DEFAULTSIZE = 0x00000040
                WM_SETICON = 0x0080
                ICON_BIG = 1
                ICON_SMALL = 0
                # Load icon at taskbar size (32x32) and title bar size (16x16)
                hicon_big = ctypes.windll.user32.LoadImageW(
                    0, icon_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE
                )
                hicon_small = ctypes.windll.user32.LoadImageW(
                    0, icon_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE
                )
                if hicon_big:
                    ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon_big)
                if hicon_small:
                    ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon_small)

            # Refresh to apply
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
            ctypes.windll.user32.ShowWindow(hwnd, 5)  # SW_SHOW
        except Exception as e:
            print(f"[WARN] Taskbar show failed: {e}")

        # ── Build UI ──
        self._create_header()

        # Footer (autostart + Save & Start + minimize) spans the full width and
        # is always pinned to the bottom, so the main CTA is never scrolled away.
        self.footer_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.footer_bar.pack(side="bottom", fill="x", padx=22, pady=(2, 14))

        # Two columns side by side for the 4:3 layout. Each scrolls independently
        # so nothing is clipped on smaller screens / higher DPI.
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(side="top", fill="both", expand=True, padx=10, pady=(2, 4))

        self.content_frame = ctk.CTkScrollableFrame(
            body, fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
            scrollbar_button_hover_color=COLORS["border_light"],
        )
        self.content_frame.pack(side="left", fill="both", expand=True, padx=(4, 7))

        self.content_right = ctk.CTkScrollableFrame(
            body, fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
            scrollbar_button_hover_color=COLORS["border_light"],
        )
        self.content_right.pack(side="left", fill="both", expand=True, padx=(7, 4))

        # Left column: status + system + model + language. Right column: hotkeys
        # + custom words (routed inside _create_form_section).
        self._create_status_section()
        self._create_system_checks_section()
        self._create_form_section()
        self._create_footer()

        # ── Drag support ──
        self.bind("<Button-1>", self.start_move)
        self.bind("<B1-Motion>", self.do_move)

    # ─── HEADER ──────────────────────────────────────────────────────────
    def _create_header(self):
        # Round the window corners via Windows DWM API
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            DWMWA_WINDOW_CORNER_PREFERENCE = 33
            DWMWCP_ROUND = ctypes.c_int(2)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_WINDOW_CORNER_PREFERENCE,
                ctypes.byref(DWMWCP_ROUND), ctypes.sizeof(DWMWCP_ROUND)
            )
        except Exception as e:
            print(f"[WARN] DWM corner rounding failed: {e}")

        header = ctk.CTkFrame(self, fg_color="transparent", height=50)
        header.pack(fill="x", padx=22, pady=(18, 8))

        # Title (left-aligned)
        title = ctk.CTkLabel(
            header, text="FluidText AI",
            font=("Segoe UI Semibold", 17, "bold"), text_color=COLORS["text_main"]
        )
        title.place(relx=0.5, rely=0.5, anchor="center")

        # Close ✕ (right)
        self.btn_close = ctk.CTkButton(
            header, text="✕", width=28, height=28,
            fg_color="transparent", text_color=COLORS["text_sec"],
            hover_color=COLORS["border"], corner_radius=14,
            font=("Segoe UI", 13), command=self.minimize_to_tray
        )
        self.btn_close.pack(side="right")

        # Draggable
        for w in (header, title):
            w.bind("<Button-1>", self.start_move)
            w.bind("<B1-Motion>", self.do_move)

    # ─── STATUS PILL ─────────────────────────────────────────────────────
    def _create_status_section(self):
        self.status_frame = ctk.CTkFrame(
            self.content_frame, fg_color=COLORS["card_bg"],
            border_color=COLORS["border"], border_width=1, corner_radius=12
        )
        self.status_frame.pack(fill="x", pady=(0, 10))

        # Green dot via canvas
        self.status_dot = ctk.CTkCanvas(
            self.status_frame, width=14, height=14,
            bg=COLORS["card_bg"], highlightthickness=0
        )
        self.status_dot.pack(side="left", padx=(16, 8), pady=14)
        self.status_dot.create_oval(2, 2, 12, 12, fill=COLORS["text_sec"], outline="")

        # Status text
        self.status_label = ctk.CTkLabel(
            self.status_frame, text="CHECKING SYSTEM...",
            font=("Segoe UI Semibold", 11, "bold"), text_color=COLORS["text_sec"]
        )
        self.status_label.pack(side="left")

        # Checkmark (right)
        self.status_check = ctk.CTkLabel(
            self.status_frame, text="…",
            font=("Segoe UI", 15, "bold"), text_color=COLORS["text_sec"]
        )
        self.status_check.pack(side="right", padx=16)

    # ─── SYSTEM CHECKS SECTION ───────────────────────────────────────────
    def _create_system_checks_section(self):
        """Create the GPU / NVIDIA DLL status panel."""
        self.sys_frame = ctk.CTkFrame(
            self.content_frame, fg_color=COLORS["card_bg"],
            border_color=COLORS["border"], border_width=1, corner_radius=10
        )
        self.sys_frame.pack(fill="x", pady=(0, 14))

        # Header row
        header = ctk.CTkFrame(self.sys_frame, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=(10, 4))

        ctk.CTkLabel(
            header, text="⚙  SYSTEM",
            font=("Segoe UI Semibold", 10, "bold"), text_color=COLORS["text_label"]
        ).pack(side="left")

        self.gpu_summary_label = ctk.CTkLabel(
            header, text="checking...",
            font=("Segoe UI", 10), text_color=COLORS["text_sec"]
        )
        self.gpu_summary_label.pack(side="right")

        # DLL status rows
        self._dll_labels = {}
        dll_checks = [
            ("cuda",     "CUDA Devices"),
            ("cublas",   "cuBLAS"),
            ("cublaslt", "cuBLAS Lt"),
            ("cudnn",    "cuDNN"),
        ]
        for key, display_name in dll_checks:
            row = ctk.CTkFrame(self.sys_frame, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=1)

            ctk.CTkLabel(
                row, text=display_name,
                font=("Segoe UI", 11), text_color=COLORS["text_sec"],
                anchor="w", width=120
            ).pack(side="left")

            status_lbl = ctk.CTkLabel(
                row, text="…",
                font=("Segoe UI", 11), text_color=COLORS["text_sec"],
                anchor="e"
            )
            status_lbl.pack(side="right")
            self._dll_labels[key] = status_lbl

        # Bottom pad
        ctk.CTkFrame(self.sys_frame, fg_color="transparent", height=6).pack()

        # Run check in background
        threading.Thread(target=self._run_system_checks, daemon=True).start()

    def _run_system_checks(self):
        """Run NVIDIA DLL checks in background and update UI."""
        try:
            results = check_nvidia_dlls()
        except Exception as e:
            results = {
                'cuda_available': False, 'cuda_device_count': 0,
                'cublas': False, 'cublaslt': False, 'cudnn': False,
                'details': {'error': str(e)}
            }
        self.after(0, lambda: self._apply_system_check_results(results))

    def _apply_system_check_results(self, results):
        """Update the system checks UI with results."""
        cuda_ok = results['cuda_available']
        count = results['cuda_device_count']
        vram_mb = results.get('vram_mb', 0)
        vram_str = f" ({vram_mb / 1024:.1f} GB)" if vram_mb > 0 else ""

        if results.get('is_mac'):
            # macOS uses the MLX (Apple Silicon) backend — there are no CUDA DLLs.
            mlx_ok = results.get('mlx_available', False)
            self._dll_labels['cuda'].configure(
                text=f"✓  Apple Silicon (MLX){vram_str}" if mlx_ok else "✗  MLX not installed",
                text_color=COLORS['success'] if mlx_ok else COLORS['danger']
            )
            for key in ('cublas', 'cublaslt', 'cudnn'):
                self._dll_labels[key].configure(text="—  n/a", text_color=COLORS['text_sec'])
            all_ok = mlx_ok
            self.gpu_summary_label.configure(
                text="MLX Ready ✓" if mlx_ok else "CPU Mode",
                text_color=COLORS['success'] if mlx_ok else COLORS['text_sec']
            )
        else:
            # CUDA row
            self._dll_labels['cuda'].configure(
                text=f"✓  {count} device(s){vram_str}" if cuda_ok else "✗  No CUDA",
                text_color=COLORS['success'] if cuda_ok else COLORS['danger']
            )
            # DLL rows
            all_ok = cuda_ok
            for key in ('cublas', 'cublaslt', 'cudnn'):
                found = results.get(key, False)
                all_ok = all_ok and found
                self._dll_labels[key].configure(
                    text="✓  Found" if found else "✗  Missing",
                    text_color=COLORS['success'] if found else COLORS['danger']
                )
            # Summary label
            if all_ok:
                self.gpu_summary_label.configure(text="GPU Ready ✓", text_color=COLORS['success'])
            elif cuda_ok:
                self.gpu_summary_label.configure(text="DLLs Missing ⚠", text_color="#e8a838")
            else:
                self.gpu_summary_label.configure(text="CPU Mode", text_color=COLORS['text_sec'])

        # Update the top status pill
        if all_ok:
            self.status_dot.delete("all")
            self.status_dot.create_oval(2, 2, 12, 12, fill=COLORS['success'], outline="")
            self.status_label.configure(text="SYSTEM READY", text_color=COLORS['text_sec'])
            self.status_check.configure(text="✓", text_color=COLORS['success'])
        elif cuda_ok:
            self.status_dot.delete("all")
            self.status_dot.create_oval(2, 2, 12, 12, fill="#e8a838", outline="")
            self.status_label.configure(text="MISSING DLLs", text_color="#e8a838")
            self.status_check.configure(text="⚠", text_color="#e8a838")
        else:
            self.status_dot.delete("all")
            self.status_dot.create_oval(2, 2, 12, 12, fill=COLORS['text_sec'], outline="")
            self.status_label.configure(text="CPU MODE", text_color=COLORS['text_sec'])
            self.status_check.configure(text="—", text_color=COLORS['text_sec'])

        # Auto-suggest model based on VRAM
        if cuda_ok and vram_mb > 0 and hasattr(self, 'combo_model'):
            if not self.settings_manager.get("optimal_model_selected"):
                optimal_model = "large-v3-turbo"
                if vram_mb < 2000:
                    optimal_model = "base"
                elif vram_mb < 3000:
                    optimal_model = "small"
                elif vram_mb < 6000:
                    optimal_model = "medium"
                
                if hasattr(self, '_model_id_to_display'):
                    display = self._model_id_to_display.get(optimal_model, optimal_model)
                    self.combo_model.set(display)
                    self._update_model_status()
                    
                    self.model_status_label.configure(text=f"✨ Auto-selected {optimal_model} based on your GPU", text_color=COLORS["success"])
                    
                    self.settings_manager.save_settings({
                        "model_size": optimal_model,
                        "optimal_model_selected": True
                    })

    # ─── FORM SECTION ────────────────────────────────────────────────────
    def _create_form_section(self):
        # ── MODEL ──
        self._section_label("🧠", "MODEL")

        # All sensible faster-whisper models with approximate VRAM usage.
        # large-v3-turbo: near large-v3 accuracy at a fraction of the compute
        # (~6 GB VRAM, several times faster) — the recommended default.
        self.MODEL_LIST = [
            ("tiny",           "tiny             (~1 GB VRAM)"),
            ("base",           "base             (~1 GB VRAM)"),
            ("small",          "small            (~2 GB VRAM)"),
            ("medium",         "medium           (~5 GB VRAM)"),
            ("large-v3-turbo", "large-v3-turbo   (~6 GB · fast ⚡)"),
            ("large-v2",       "large-v2         (~10 GB VRAM)"),
            ("large-v3",       "large-v3         (~10 GB VRAM)"),
        ]
        self._model_display_to_id = {display: mid for mid, display in self.MODEL_LIST}
        self._model_id_to_display = {mid: display for mid, display in self.MODEL_LIST}
        model_displays = [d for _, d in self.MODEL_LIST]

        self.combo_model = ctk.CTkComboBox(
            self.content_frame,
            values=model_displays,
            fg_color=COLORS["card_bg"], border_color=COLORS["border"],
            button_color=COLORS["card_bg"], button_hover_color=COLORS["border_light"],
            dropdown_fg_color=COLORS["card_bg"],
            dropdown_hover_color=COLORS["border"],
            text_color=COLORS["text_main"], width=336, height=48,
            corner_radius=10, font=("Consolas", 12)
        )
        current_model = self.settings_manager.get("model_size")
        display = self._model_id_to_display.get(current_model, model_displays[-1])
        self.combo_model.set(display)
        self.combo_model.pack(fill="x", pady=(6, 4))
        self.combo_model.configure(command=lambda _: self._update_model_status())

        # Status + Download button row
        status_row = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        status_row.pack(fill="x", pady=(0, 14))

        self.model_status_label = ctk.CTkLabel(
            status_row, text="",
            font=("Segoe UI", 10), text_color=COLORS["text_sec"],
            anchor="w"
        )
        self.model_status_label.pack(side="left", padx=4)

        self.btn_download = ctk.CTkButton(
            status_row, text="⬇  Download",
            fg_color=COLORS["card_bg"], text_color=COLORS["accent_blue"],
            border_color=COLORS["border_light"], border_width=1,
            hover_color=COLORS["border"], corner_radius=8,
            font=("Segoe UI Semibold", 10, "bold"),
            width=110, height=28,
            command=self._download_model
        )
        self.btn_download.pack(side="right", padx=4)

        self._update_model_status()

        # ── LANGUAGE ──
        self._lang_section_start = self._section_label("🌐", "LANGUAGE")
        lang_values = list(LANGUAGES.values())
        self.combo_lang = ctk.CTkComboBox(
            self.content_frame,
            values=lang_values,
            fg_color=COLORS["card_bg"], border_color=COLORS["border"],
            button_color=COLORS["card_bg"], button_hover_color=COLORS["border_light"],
            dropdown_fg_color=COLORS["card_bg"],
            dropdown_hover_color=COLORS["border"],
            text_color=COLORS["text_main"], width=336, height=48,
            corner_radius=10, font=("Segoe UI", 13)
        )
        # Set current language display
        current_lang = self.settings_manager.get("language")
        display = LANGUAGES.get(current_lang, "Deutsch (de)")
        self.combo_lang.set(display)
        self.combo_lang.pack(fill="x", pady=(6, 18))

        # ── HOTKEY (push-to-talk) ── right column
        right = self.content_right
        self._section_label("⌨", "HOTKEY", parent=right)
        ctk.CTkLabel(
            right,
            text="Hold to dictate. Set up to two — either one triggers it.",
            font=("Segoe UI", 10), text_color=COLORS["text_sec"], anchor="w",
            justify="left",
        ).pack(anchor="w", pady=(2, 4))

        self.current_hotkey = self.settings_manager.get("hotkey") or ""
        self.current_hotkey2 = self.settings_manager.get("hotkey2") or ""

        self.btn_hotkey = self._build_hotkey_row(
            self.current_hotkey, self.record_hotkey, clear_cmd=None, parent=right
        )
        self.btn_hotkey2 = self._build_hotkey_row(
            self.current_hotkey2, self.record_hotkey2,
            clear_cmd=self.clear_hotkey2, placeholder="+  Add second hotkey", parent=right
        )
        # Bottom spacer to match the previous section spacing.
        ctk.CTkFrame(right, fg_color="transparent", height=8).pack()

        # ── CUSTOM VOCABULARY ── right column
        self._section_label("📖", "CUSTOM WORDS", parent=right)
        ctk.CTkLabel(
            right,
            text="One per line. Use  misheard => correct  to fix recurring errors.",
            font=("Segoe UI", 10), text_color=COLORS["text_sec"], anchor="w",
            justify="left",
        ).pack(anchor="w", pady=(2, 4))

        self.txt_vocab = ctk.CTkTextbox(
            right,
            height=180, fg_color=COLORS["card_bg"],
            border_color=COLORS["border_light"], border_width=1,
            corner_radius=10, font=("Consolas", 12),
            text_color=COLORS["text_main"],
        )
        self.txt_vocab.pack(fill="both", expand=True, pady=(0, 8))
        self.txt_vocab.insert("1.0", self._vocab_settings_to_text())

    def _vocab_settings_to_text(self):
        """Render saved vocabulary + replacements back into the textbox format."""
        lines = list(self.settings_manager.get("vocabulary") or [])
        for wrong, right in (self.settings_manager.get("replacements") or {}).items():
            lines.append(f"{wrong} => {right}")
        return "\n".join(lines)

    def _parse_vocab_text(self):
        """Parse the textbox into (vocabulary list, replacements dict).
        A line with '=>' (or '=') is a correction; anything else is a term
        that biases recognition toward the user's preferred spelling."""
        vocabulary, replacements = [], {}
        raw = self.txt_vocab.get("1.0", "end") if hasattr(self, "txt_vocab") else ""
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            sep = "=>" if "=>" in line else ("=" if "=" in line else None)
            if sep:
                wrong, _, right = line.partition(sep)
                wrong, right = wrong.strip(), right.strip()
                if wrong:
                    replacements[wrong] = right
                    # Bias toward the corrected spelling too.
                    if right:
                        vocabulary.append(right)
            else:
                vocabulary.append(line)
        return vocabulary, replacements

    # ─── FOOTER (autostart + buttons) ────────────────────────────────────
    def _create_footer(self):
        footer = self.footer_bar
        # ── Autostart row ──
        row = ctk.CTkFrame(footer, fg_color="transparent")
        row.pack(fill="x", pady=(5, 8))

        text_col = ctk.CTkFrame(row, fg_color="transparent")
        text_col.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            text_col, text="Start with Windows",
            font=("Segoe UI Semibold", 13, "bold"), text_color=COLORS["text_main"],
            anchor="w"
        ).pack(anchor="w")

        self.autostart_sub = ctk.CTkLabel(
            text_col, text="Launch tool on system boot",
            font=("Segoe UI", 11), text_color=COLORS["text_sec"],
            anchor="w"
        )
        self.autostart_sub.pack(anchor="w")

        self.var_autostart = ctk.BooleanVar(value=self.check_autostart())
        self.switch_autostart = ctk.CTkSwitch(
            row, text="", variable=self.var_autostart,
            command=self.toggle_autostart,
            progress_color=COLORS["switch_on"],
            button_color="white",
            button_hover_color="#e0e0e0",
            fg_color=COLORS["border"],
            height=24, width=48
        )
        self.switch_autostart.pack(side="right", pady=5)

        # Spacer
        ctk.CTkFrame(footer, fg_color="transparent", height=8).pack()

        # ── Action buttons side by side (modern wide layout) ──
        btn_row = ctk.CTkFrame(footer, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, 4))

        # Save & Start – main CTA (takes the remaining width)
        self.btn_save = ctk.CTkButton(
            btn_row, text="Save & Start  ▸",
            fg_color=COLORS["accent"], text_color="#0a0a0e",
            hover_color=COLORS["accent_hover"],
            height=54, corner_radius=14,
            font=("Segoe UI Semibold", 14, "bold"),
            command=self.launch_overlay
        )
        self.btn_save.pack(side="left", fill="x", expand=True, padx=(0, 8))

        # Minimize to tray – explicit, so the ✕ isn't the only (unclear) way
        self.btn_tray = ctk.CTkButton(
            btn_row, text="▾  In den Tray minimieren", width=240,
            fg_color="transparent", text_color=COLORS["text_sec"],
            hover_color=COLORS["border"], border_color=COLORS["border_light"],
            border_width=1, height=54, corner_radius=14,
            font=("Segoe UI Semibold", 12, "bold"),
            command=self.minimize_to_tray
        )
        self.btn_tray.pack(side="right")
        ctk.CTkLabel(
            footer,
            text="Läuft im Hintergrund weiter – Diktieren bleibt aktiv.",
            font=("Segoe UI", 9), text_color=COLORS["text_sec"]
        ).pack(pady=(0, 2))

    def _get_selected_model_id(self):
        """Get the model ID from the display string."""
        display = self.combo_model.get()
        return self._model_display_to_id.get(display, display)

    def _update_model_status(self):
        """Update the model status label based on whether model files are cached locally."""
        model_id = self._get_selected_model_id()
        cached = self._is_model_cached(model_id)
        if cached:
            self.model_status_label.configure(
                text="✓  Model downloaded and ready",
                text_color=COLORS["success"]
            )
            self.btn_download.configure(
                text="✓  Verified",
                text_color=COLORS["success"],
                border_color=COLORS["border"],
                state="disabled"
            )
        else:
            self.model_status_label.configure(
                text="⬇  Not downloaded yet",
                text_color="#e8a838"
            )
            self.btn_download.configure(
                text="⬇  Download",
                text_color=COLORS["accent_blue"],
                border_color=COLORS["border_light"],
                state="normal"
            )

    # Approximate download sizes in MB for progress estimation
    MODEL_SIZES_MB = {
        "tiny": 75, "base": 145, "small": 465,
        "medium": 1500, "large-v2": 3000, "large-v3": 3000,
        "large-v3-turbo": 1620,
    }

    def _get_model_path(self, model_id):
        user_data = appdirs.user_data_dir("FluidText", "FluidTextAI")
        return os.path.join(user_data, "models", model_id)

    def _download_model(self):
        """Download the selected model in a background thread with progress."""
        if self._downloading:
            return
        self._downloading = True
        model_id = self._get_selected_model_id()

        self.btn_download.configure(
            text="⏳  Downloading...",
            text_color="#e8a838",
            state="disabled"
        )

        # Create progress bar if not exists
        if not hasattr(self, 'progress_bar'):
            self.progress_bar = ctk.CTkProgressBar(
                self.content_frame,
                fg_color=COLORS["border"],
                progress_color=COLORS["accent_blue"],
                height=6, corner_radius=3
            )
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", pady=(0, 4), before=self._lang_section_start)

        self.model_status_label.configure(
            text=f"Downloading {model_id}... 0%",
            text_color="#e8a838"
        )

        # Use persistent local path for final storage
        local_dir = self._get_model_path(model_id)
        os.makedirs(local_dir, exist_ok=True)
        
        # Poll the actual download target directory for progress
        self._dl_cache_path = local_dir
        self._dl_model_id = model_id
        self._dl_total_mb = self.MODEL_SIZES_MB.get(model_id, 1000)

        # Start progress polling
        self._poll_progress()

        threading.Thread(target=self._do_download, args=(model_id, local_dir), daemon=True).start()

    def _get_dir_size_mb(self, path):
        """Get total size of a directory in MB."""
        total = 0
        try:
            for root, dirs, files in os.walk(path):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        total += os.path.getsize(fp)
                    except:
                        pass
        except:
            pass
        return total / (1024 * 1024)

    def _poll_progress(self):
        """Poll download directory size to update progress bar."""
        if not self._downloading:
            return
        current_mb = self._get_dir_size_mb(self._dl_cache_path)
        ratio = min(current_mb / self._dl_total_mb, 0.99)
        pct = int(ratio * 100)
        self.progress_bar.set(ratio)
        self.model_status_label.configure(
            text=f"Downloading {self._dl_model_id}... {pct}%  ({current_mb:.0f}/{self._dl_total_mb:.0f} MB)"
        )
        self.after(500, self._poll_progress)

    def _do_download(self, model_id, local_dir):
        """Background download of the model to local dir."""
        try:
            # Fix for PyInstaller --noconsole: sys.stdout/stderr are None,
            # which crashes tqdm (used by huggingface_hub).
            # Redirect to devnull so tqdm.write() doesn't crash.
            if getattr(sys, 'frozen', False):
                import io
                if sys.stdout is None:
                    sys.stdout = open(os.devnull, 'w')
                if sys.stderr is None:
                    sys.stderr = open(os.devnull, 'w')
                # Fix SSL certificates
                try:
                    import certifi
                    os.environ['SSL_CERT_FILE'] = certifi.where()
                    os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
                except Exception:
                    pass

            from huggingface_hub import snapshot_download
            if IS_MAC:
                # macOS uses MLX models, cached in the shared HF cache.
                from transcriber import MLX_REPOS
                repo_id = MLX_REPOS.get(model_id, f"mlx-community/whisper-{model_id}")
                snapshot_download(repo_id)
            else:
                # Resolve the HF repo from faster-whisper's own registry. Not every
                # model lives under "Systran/..." (e.g. large-v3-turbo is hosted by
                # mobiuslabsgmbh), so hard-coding the org breaks newer models.
                try:
                    from faster_whisper.utils import _MODELS
                    repo_id = _MODELS.get(model_id, f"Systran/faster-whisper-{model_id}")
                except Exception:
                    repo_id = f"Systran/faster-whisper-{model_id}"
                snapshot_download(
                    repo_id,
                    local_dir=local_dir,
                    local_dir_use_symlinks=False
                )
            # Verify download
            if IS_MAC:
                # MLX downloads land in the HF cache, not local_dir.
                ok, err = (self._is_model_cached(model_id), "Model not found in cache")
            else:
                ok, err = self._verify_model_download(local_dir)
            self._downloading = False
            if ok:
                self.after(0, lambda: self._on_download_done(model_id, success=True))
            else:
                self.after(0, lambda: self._on_download_done(model_id, success=False, error=err))
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"[ERR] Download failed: {e}")
            # Write to log file so errors are visible even with --noconsole
            try:
                log_path = os.path.join(os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else '.', 'download_error.log')
                with open(log_path, 'w') as f:
                    f.write(f"Download failed for {model_id}\n{tb}\n")
            except:
                pass
            self._downloading = False
            self.after(0, lambda: self._on_download_done(model_id, success=False, error=str(e)))

    def _verify_model_download(self, model_dir):
        """Verify that a downloaded model directory contains the required files."""
        if not os.path.exists(model_dir):
            return False, "Directory does not exist"

        config = os.path.join(model_dir, "config.json")
        if not os.path.exists(config):
            return False, "Missing config.json"

        # Check for the actual model binary (model.bin or *.bin)
        model_bin = os.path.join(model_dir, "model.bin")
        bin_files = glob.glob(os.path.join(model_dir, "*.bin"))
        if not os.path.exists(model_bin) and not bin_files:
            return False, "Missing model binary file"

        return True, ""

    def _on_download_done(self, model_id, success=True, error=""):
        self._downloading = False
        if hasattr(self, 'progress_bar'):
            self.progress_bar.set(1.0 if success else 0)
            self.progress_bar.pack_forget()
        if success:
            self.model_status_label.configure(
                text=f"✓  {model_id} downloaded and ready",
                text_color=COLORS["success"]
            )
            self.btn_download.configure(
                text="✓  Verified",
                text_color=COLORS["success"],
                border_color=COLORS["border"],
                state="disabled"
            )
        else:
            self.model_status_label.configure(
                text=f"✗  Download failed: {error[:40]}",
                text_color=COLORS["danger"]
            )
            self.btn_download.configure(
                text="⬇  Retry",
                text_color=COLORS["accent_blue"],
                border_color=COLORS["border_light"],
                state="normal"
            )

    def _is_model_cached(self, model_id):
        """Check if the selected model is already downloaded locally."""
        if IS_MAC:
            # MLX models live in the shared Hugging Face cache, not our models dir.
            try:
                from transcriber import MLX_REPOS
                from huggingface_hub import snapshot_download
                repo = MLX_REPOS.get(model_id, f"mlx-community/whisper-{model_id}")
                snapshot_download(repo, local_files_only=True)
                return True
            except Exception:
                return False
        path = self._get_model_path(model_id)
        # Check for config.json AND model binary
        has_config = os.path.exists(os.path.join(path, "config.json"))
        has_model = os.path.exists(os.path.join(path, "model.bin")) or bool(glob.glob(os.path.join(path, "*.bin")))
        return has_config and has_model


    # ─── Helpers ─────────────────────────────────────────────────────────
    def _tcl_bgerror(self, msg):
        if "invalid command name" in str(msg) or "application has been destroyed" in str(msg):
            return ""
        sys.stderr.write(f"[Tcl] {msg}\n")
        return ""

    def _section_label(self, icon, text, parent=None):
        lbl = ctk.CTkLabel(
            parent or self.content_frame,
            text=f"{icon}  {text}",
            font=("Segoe UI Semibold", 10, "bold"),
            text_color=COLORS["text_label"]
        )
        lbl.pack(anchor="w", pady=(0, 0))
        return lbl

    # ─── Drag logic ──────────────────────────────────────────────────────
    def start_move(self, event):
        self.drag_x = event.x
        self.drag_y = event.y

    def do_move(self, event):
        x = self.winfo_x() + (event.x - self.drag_x)
        y = self.winfo_y() + (event.y - self.drag_y)
        self.geometry(f"+{x}+{y}")

    # ─── Autostart ───────────────────────────────────────────────────────
    # Delegated to the platform layer: registry Run key on Windows, a
    # LaunchAgent .plist on macOS. The dashboard only flips the switch.
    def check_autostart(self):
        try:
            return get_autostart().is_enabled()
        except Exception as e:
            print(f"Autostart check error: {e}")
            return False

    def toggle_autostart(self):
        try:
            mgr = get_autostart()
            if self.var_autostart.get():
                mgr.enable()
                # enable() verifies the write; reaching here means it stuck.
                self._set_autostart_sub("✓  Enabled — starts with Windows", COLORS["success"])
            else:
                mgr.disable()
                self._set_autostart_sub("Launch tool on system boot", COLORS["text_sec"])
        except Exception as e:
            print(f"Autostart Error: {e}")
            # Surface the failure clearly instead of silently flipping back.
            try:
                self.var_autostart.set(self.check_autostart())
            except Exception:
                pass
            self._set_autostart_sub("✗  Could not enable autostart", COLORS["danger"])

    def _set_autostart_sub(self, text, color):
        try:
            self.autostart_sub.configure(text=text, text_color=color)
        except Exception:
            pass

    # ─── Hotkey recording ────────────────────────────────────────────────
    def _build_hotkey_row(self, current, record_cmd, clear_cmd=None, placeholder="", parent=None):
        """Build one hotkey input row (button + edit, plus an optional clear
        button for the optional second hotkey). Returns the main button."""
        frame = ctk.CTkFrame(
            parent or self.content_frame, fg_color=COLORS["card_bg"],
            border_color=COLORS["border_light"], border_width=1, corner_radius=10
        )
        frame.pack(fill="x", pady=(6, 6), ipady=4)

        label = current.upper().replace("+", " + ") if current else placeholder
        btn = ctk.CTkButton(
            frame, text=label,
            fg_color="transparent",
            text_color=COLORS["accent"] if current else COLORS["text_sec"],
            hover_color=COLORS["border"], font=("Consolas", 14, "bold"),
            height=38, anchor="w", command=record_cmd
        )
        btn.pack(side="left", fill="x", expand=True, padx=(8, 0), pady=4)

        # Pencil edit icon (right)
        ctk.CTkButton(
            frame, text="✏", width=36, height=36,
            fg_color="transparent", text_color=COLORS["text_sec"],
            hover_color=COLORS["border"], corner_radius=8,
            font=("Segoe UI", 15), command=record_cmd
        ).pack(side="right", padx=6, pady=4)

        # Optional clear (✕) for the optional second hotkey
        if clear_cmd is not None:
            ctk.CTkButton(
                frame, text="✕", width=30, height=36,
                fg_color="transparent", text_color=COLORS["text_sec"],
                hover_color=COLORS["border"], corner_radius=8,
                font=("Segoe UI", 13), command=clear_cmd
            ).pack(side="right", padx=(0, 0), pady=4)

        return btn

    def record_hotkey(self):
        self.btn_hotkey.configure(
            text="⏳  Listening...",
            fg_color=COLORS["accent"], text_color="#0a0a0e"
        )
        self.after(200, lambda: threading.Thread(target=self._wait_for_hotkey, daemon=True).start())

    def _wait_for_hotkey(self):
        try:
            hotkey = read_hotkey()
            self.current_hotkey = normalize_hotkey(hotkey)
            self.after(0, self._update_hotkey_ui)
        except:
            self.after(0, self._update_hotkey_ui)

    def _update_hotkey_ui(self):
        display = self.current_hotkey.upper().replace("+", " + ")
        self.btn_hotkey.configure(
            text=display, fg_color="transparent",
            text_color=COLORS["accent"]
        )

    # Second (optional) push-to-talk hotkey
    def record_hotkey2(self):
        self.btn_hotkey2.configure(
            text="⏳  Listening...",
            fg_color=COLORS["accent"], text_color="#0a0a0e"
        )
        self.after(200, lambda: threading.Thread(target=self._wait_for_hotkey2, daemon=True).start())

    def _wait_for_hotkey2(self):
        try:
            hotkey = read_hotkey()
            self.current_hotkey2 = normalize_hotkey(hotkey)
            self.after(0, self._update_hotkey2_ui)
        except:
            self.after(0, self._update_hotkey2_ui)

    def _update_hotkey2_ui(self):
        if self.current_hotkey2:
            self.btn_hotkey2.configure(
                text=self.current_hotkey2.upper().replace("+", " + "),
                fg_color="transparent", text_color=COLORS["accent"]
            )
        else:
            self.btn_hotkey2.configure(
                text="+  Add second hotkey",
                fg_color="transparent", text_color=COLORS["text_sec"]
            )

    def clear_hotkey2(self):
        self.current_hotkey2 = ""
        self._update_hotkey2_ui()

    # ─── Save / Launch ───────────────────────────────────────────────────
    def save_settings(self):
        # Resolve language code from display string
        lang_display = self.combo_lang.get()
        lang_code = LANG_DISPLAY_TO_CODE.get(lang_display, lang_display)

        vocabulary, replacements = self._parse_vocab_text()
        self.settings_manager.save_settings({
            "model_size": self._get_selected_model_id(),
            "language": lang_code,
            "hotkey": self.current_hotkey,
            "hotkey2": self.current_hotkey2,
            "vocabulary": vocabulary,
            "replacements": replacements
        })
        # Visual feedback
        orig = self.btn_save.cget("text")
        self.btn_save.configure(
            text="✓  Saved", text_color=COLORS["success"],
            border_color=COLORS["success"]
        )
        self.after(1500, lambda: self.btn_save.configure(
            text=orig, text_color=COLORS["accent_blue"],
            border_color=COLORS["border_light"]
        ))

    def launch_overlay(self):
        self.save_settings()
        self.destroy()
        if self.on_start_callback:
            self.on_start_callback(hidden=False)

    def minimize_to_tray(self):
        self.save_settings()
        self.destroy()
        if self.on_start_callback:
            self.on_start_callback(hidden=True)


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    d = ModernDashboard(lambda **kwargs: print(f"Launch with {kwargs}"))
    d.mainloop()
