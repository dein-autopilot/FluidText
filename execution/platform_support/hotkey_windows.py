"""Windows hotkey support, backed by the ``keyboard`` library."""

import keyboard


class WindowsHotkeyMonitor:
    def is_pressed(self, hotkey):
        return keyboard.is_pressed(hotkey)


def read_hotkey():
    """Block until a key/combo is pressed and return it as a string."""
    return keyboard.read_hotkey(suppress=False)
