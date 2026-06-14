
import sys

IS_MAC = sys.platform == "darwin"


class TextInjector:
    """Types transcribed text into the focused application.

    Windows uses the ``keyboard`` library; macOS uses ``pynput`` (which needs
    the Accessibility permission). The public API is identical on both.
    """

    def __init__(self):
        if IS_MAC:
            from pynput.keyboard import Controller
            self._controller = Controller()
            self._backend = "pynput"
        else:
            import keyboard
            self._keyboard = keyboard
            self._backend = "keyboard"

    def type_text(self, text):
        if not text:
            print("[DEBUG] Injector received empty text.")
            return

        print(f"[DEBUG] Injector typing: '{text}'")
        try:
            if self._backend == "pynput":
                self._controller.type(text + " ")
            else:
                self._keyboard.write(text + " ")
            print("[DEBUG] Keyboard write command sent.")
        except Exception as e:
            print(f"[ERROR] Keyboard write failed: {e}")
