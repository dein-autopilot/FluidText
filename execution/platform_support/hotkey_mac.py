"""macOS hotkey support, backed by ``pynput``.

``keyboard`` is effectively Windows-only, so on macOS we run a global
``pynput`` listener (its own thread, with a Quartz event tap) and track which
keys are currently held. ``is_pressed`` then answers the push-to-talk loop.

Requires the **Input Monitoring** permission (System Settings → Privacy &
Security). Without it the listener silently receives no events.
"""

import threading

from pynput import keyboard as _kb

# Map pynput special keys to the normalized names used throughout the app
# (see utils.normalize_hotkey). Each key contributes one or more aliases so a
# generic token like "ctrl" matches either the left or right modifier.
_SPECIAL_ALIASES = {
    _kb.Key.ctrl_l: {"ctrl", "left ctrl"},
    _kb.Key.ctrl_r: {"ctrl", "right ctrl"},
    _kb.Key.shift_l: {"shift", "left shift"},
    _kb.Key.shift_r: {"shift", "right shift"},
    _kb.Key.shift: {"shift"},
    _kb.Key.alt_l: {"alt", "left alt", "option"},
    _kb.Key.alt_r: {"alt", "right alt", "alt gr", "option"},
    _kb.Key.cmd: {"cmd", "win", "left cmd"},
    _kb.Key.cmd_r: {"cmd", "win", "right cmd"},
    _kb.Key.space: {"space"},
    _kb.Key.enter: {"enter"},
    _kb.Key.tab: {"tab"},
    _kb.Key.esc: {"esc", "escape"},
    _kb.Key.backspace: {"backspace"},
    _kb.Key.delete: {"delete"},
    _kb.Key.up: {"up"},
    _kb.Key.down: {"down"},
    _kb.Key.left: {"left"},
    _kb.Key.right: {"right"},
    _kb.Key.home: {"home"},
    _kb.Key.end: {"end"},
    _kb.Key.page_up: {"page up"},
    _kb.Key.page_down: {"page down"},
}

# Preferred single name for *recording* a hotkey (most specific wins).
_PRIMARY_NAME = {
    _kb.Key.ctrl_l: "left ctrl", _kb.Key.ctrl_r: "right ctrl",
    _kb.Key.shift_l: "left shift", _kb.Key.shift_r: "right shift",
    _kb.Key.shift: "shift",
    _kb.Key.alt_l: "left alt", _kb.Key.alt_r: "right alt",
    _kb.Key.cmd: "left cmd", _kb.Key.cmd_r: "right cmd",
    _kb.Key.space: "space", _kb.Key.enter: "enter", _kb.Key.tab: "tab",
    _kb.Key.esc: "esc", _kb.Key.up: "up", _kb.Key.down: "down",
    _kb.Key.left: "left", _kb.Key.right: "right",
}


def _aliases_for(key):
    """All normalized names a pressed key should satisfy."""
    if key in _SPECIAL_ALIASES:
        return set(_SPECIAL_ALIASES[key])
    # Function keys (f1..f20) aren't in the table above.
    name = getattr(key, "name", None)
    if name and name.startswith("f") and name[1:].isdigit():
        return {name}
    char = getattr(key, "char", None)
    if char:
        return {char.lower()}
    return set()


def _primary_for(key):
    if key in _PRIMARY_NAME:
        return _PRIMARY_NAME[key]
    name = getattr(key, "name", None)
    if name and name.startswith("f") and name[1:].isdigit():
        return name
    char = getattr(key, "char", None)
    return char.lower() if char else None


class MacHotkeyMonitor:
    def __init__(self):
        self._held = set()          # union of all aliases currently down
        self._lock = threading.Lock()
        self._listener = _kb.Listener(
            on_press=self._on_press, on_release=self._on_release
        )
        self._listener.daemon = True
        self._listener.start()

    def _on_press(self, key):
        aliases = _aliases_for(key)
        if aliases:
            with self._lock:
                self._held |= aliases

    def _on_release(self, key):
        aliases = _aliases_for(key)
        if aliases:
            with self._lock:
                self._held -= aliases

    def is_pressed(self, hotkey):
        if not hotkey:
            return False
        parts = [p.strip() for p in hotkey.split("+") if p.strip()]
        if not parts:
            return False
        with self._lock:
            held = set(self._held)
        return all(part in held for part in parts)


def read_hotkey():
    """Capture the next key/combo the user presses (for the dashboard).

    We record everything held until the first release, then build a
    ``mod+mod+key`` string from the largest combination seen.
    """
    captured = []          # ordered primary names
    seen = set()
    done = threading.Event()

    def on_press(key):
        name = _primary_for(key)
        if name and name not in seen:
            seen.add(name)
            captured.append(name)

    def on_release(key):
        if captured:
            done.set()
            return False  # stop the listener

    listener = _kb.Listener(on_press=on_press, on_release=on_release)
    listener.start()
    done.wait(timeout=15)
    try:
        listener.stop()
    except Exception:
        pass
    return "+".join(captured)
