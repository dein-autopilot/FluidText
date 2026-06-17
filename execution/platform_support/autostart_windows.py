"""Windows autostart via the per-user registry Run key.

We use ``HKCU\\...\\Run`` (winreg, stdlib) rather than a Startup-folder
shortcut. The shortcut approach depended on winshell/pywin32 DLLs and failed
silently when they were missing from the PyInstaller build.
"""

import os
import sys
import winreg

_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
_REG_NAME = "FluidText"


def _command():
    """Command line Windows should run on boot."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --autostart'
    # Dev: prefer pythonw.exe so no console window flashes on boot.
    py = sys.executable
    pyw = os.path.join(os.path.dirname(py), "pythonw.exe")
    runner = pyw if os.path.exists(pyw) else py
    main_py = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py"
    )
    return f'"{runner}" "{main_py}" --autostart'


def _remove_legacy_shortcut():
    """Delete the old Startup-folder .lnk from previous versions."""
    try:
        appdata = os.environ.get("APPDATA", "")
        if not appdata:
            return
        lnk = os.path.join(appdata, "Microsoft", "Windows", "Start Menu",
                           "Programs", "Startup", "FluidText.lnk")
        if os.path.exists(lnk):
            os.remove(lnk)
            print("[INFO] Removed legacy Startup shortcut.")
    except Exception as e:
        print(f"[WARN] Could not remove legacy shortcut: {e}")


class WindowsAutostart:
    def _stored_command(self):
        """Return the command currently registered in the Run key, or None."""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_PATH) as key:
                value, _ = winreg.QueryValueEx(key, _REG_NAME)
            return value
        except FileNotFoundError:
            return None

    def is_enabled(self):
        return self._stored_command() is not None

    def enable(self):
        """Write the Run-key value and verify the write actually took.

        Returns True on success; raises on failure so the UI can surface it
        instead of silently flipping the switch back.
        """
        _remove_legacy_shortcut()
        command = _command()
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _REG_PATH) as key:
            winreg.SetValueEx(key, _REG_NAME, 0, winreg.REG_SZ, command)
        # Read back to confirm — a silently-failed write is the whole bug we're
        # fixing, so we never trust the write blindly.
        if self._stored_command() != command:
            raise OSError("Autostart registry write could not be verified.")
        print(f"[INFO] Autostart enabled: {command}")
        return True

    def disable(self):
        _remove_legacy_shortcut()
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_PATH, 0,
                                winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, _REG_NAME)
            print("[INFO] Autostart disabled.")
        except FileNotFoundError:
            pass

    def refresh(self):
        """Self-heal: if autostart is on, rewrite the command to the *current*
        executable path. This fixes a stale entry left behind after the app
        folder was moved/renamed (Windows would otherwise try to launch a path
        that no longer exists). No-op when autostart is disabled."""
        current = self._stored_command()
        if current is None:
            return
        wanted = _command()
        if current != wanted:
            try:
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _REG_PATH) as key:
                    winreg.SetValueEx(key, _REG_NAME, 0, winreg.REG_SZ, wanted)
                print(f"[INFO] Autostart path refreshed: {wanted}")
            except Exception as e:
                print(f"[WARN] Autostart refresh failed: {e}")
