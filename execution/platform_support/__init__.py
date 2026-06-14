"""Platform abstraction layer.

The rest of the app talks to these factory functions instead of calling
OS-specific libraries directly. Each adapter is imported lazily so that a
platform's heavy/native dependency (e.g. ``keyboard`` on Windows, ``pynput``
on macOS) is only required on that platform.
"""

import os
import sys

IS_MAC = sys.platform == "darwin"
IS_WINDOWS = os.name == "nt"
IS_LINUX = sys.platform.startswith("linux")


def get_hotkey_monitor():
    """Return a monitor exposing ``is_pressed(hotkey)`` for the push-to-talk loop."""
    if IS_MAC:
        from platform_support.hotkey_mac import MacHotkeyMonitor
        return MacHotkeyMonitor()
    from platform_support.hotkey_windows import WindowsHotkeyMonitor
    return WindowsHotkeyMonitor()


def get_autostart():
    """Return an autostart manager with ``is_enabled()/enable()/disable()``."""
    if IS_MAC:
        from platform_support.autostart_mac import MacAutostart
        return MacAutostart()
    from platform_support.autostart_windows import WindowsAutostart
    return WindowsAutostart()


def read_hotkey():
    """Block until the user presses a key/combo, then return it (normalized)."""
    if IS_MAC:
        from platform_support.hotkey_mac import read_hotkey as _read
        return _read()
    from platform_support.hotkey_windows import read_hotkey as _read
    return _read()
