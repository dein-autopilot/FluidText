"""macOS autostart via a per-user LaunchAgent.

A ``~/Library/LaunchAgents/<label>.plist`` with ``RunAtLoad`` launches the app
at login. This is the standard, admin-free way to start a user app on boot.
"""

import os
import subprocess
import sys

_LABEL = "com.fluidtext.fluidtext"


def _plist_path():
    return os.path.expanduser(f"~/Library/LaunchAgents/{_LABEL}.plist")


def _program_arguments():
    """Argument vector launchd should exec on login."""
    if getattr(sys, "frozen", False):
        return [sys.executable, "--autostart"]
    main_py = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py"
    )
    return [sys.executable, main_py, "--autostart"]


def _build_plist():
    args = "".join(f"        <string>{a}</string>\n" for a in _program_arguments())
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0">\n'
        "<dict>\n"
        "    <key>Label</key>\n"
        f"    <string>{_LABEL}</string>\n"
        "    <key>ProgramArguments</key>\n"
        "    <array>\n"
        f"{args}"
        "    </array>\n"
        "    <key>RunAtLoad</key>\n"
        "    <true/>\n"
        "    <key>ProcessType</key>\n"
        "    <string>Interactive</string>\n"
        "</dict>\n"
        "</plist>\n"
    )


class MacAutostart:
    def is_enabled(self):
        return os.path.exists(_plist_path())

    def enable(self):
        path = _plist_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(_build_plist())
        # Best-effort: register now so it also works in the current session.
        # Ignore failures — the plist is loaded automatically on next login.
        try:
            subprocess.run(["launchctl", "unload", path],
                           capture_output=True, check=False)
            subprocess.run(["launchctl", "load", "-w", path],
                           capture_output=True, check=False)
        except Exception as e:
            print(f"[WARN] launchctl load failed: {e}")
        print(f"[INFO] Autostart enabled: {path}")

    def disable(self):
        path = _plist_path()
        try:
            subprocess.run(["launchctl", "unload", "-w", path],
                           capture_output=True, check=False)
        except Exception:
            pass
        if os.path.exists(path):
            os.remove(path)
        print("[INFO] Autostart disabled.")
