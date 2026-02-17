
import keyboard
import time

class TextInjector:
    def type_text(self, text):
        if not text:
            print("[DEBUG] Injector received empty text.")
            return
        
        print(f"[DEBUG] Injector typing: '{text}'")
        try:
            keyboard.write(text + " ")
            print("[DEBUG] Keyboard write command sent.")
        except Exception as e:
            print(f"[ERROR] Keyboard write failed: {e}")
