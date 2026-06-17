
import json
import os
import appdirs

class SettingsManager:
    def __init__(self, app_name="FluidText", app_author="FluidTextAI"):
        self.config_dir = appdirs.user_data_dir(app_name, app_author)
        self.config_file = os.path.join(self.config_dir, "settings.json")
        self.default_settings = {
            "model_size": "large-v3",
            "language": "de",
            "hotkey": "right ctrl",
            # Optional second push-to-talk hotkey. Either one triggers dictation.
            "hotkey2": "",
            "device": "cuda",
            "compute_type": "float16",
            "mic_index": None,
            "optimal_model_selected": False,
            # Custom vocabulary: list of words/names that bias recognition.
            # Replacements: {misheard: correct} corrections applied to output.
            "vocabulary": [],
            "replacements": {}
        }
        self.settings = self.load_settings()

    def load_settings(self):
        if not os.path.exists(self.config_file):
            self.settings = self.default_settings.copy()
            return self.settings
        
        try:
            with open(self.config_file, "r") as f:
                data = json.load(f)
                # Merge with defaults to ensure all keys exist
                settings = self.default_settings.copy()
                settings.update(data)
                self.settings = settings
                return self.settings
        except Exception as e:
            print(f"[WARN] Failed to load settings: {e}")
            self.settings = self.default_settings.copy()
            return self.settings

    def save_settings(self, new_settings):
        self.settings.update(new_settings)
        
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
            
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.settings, f, indent=4)
            print(f"[INFO] Settings saved to {self.config_file}")
        except Exception as e:
            print(f"[ERROR] Failed to save settings: {e}")

    def get(self, key):
        return self.settings.get(key, self.default_settings.get(key))
