# -*- coding: utf-8 -*-

import json
import os
import sys

# --- AppData Path Function ---
def get_appdata_path(filename="text_improver_settings.json"):
    """Gets the path for the settings file in AppData (Win) or .config (Linux/Mac)."""
    app_name = "QuickTextImprover"
    if sys.platform == 'win32':
        base_path = os.getenv('APPDATA')
        if not base_path:
            base_path = os.path.expanduser('~')
            dir_path = os.path.join(base_path, f".{app_name}")
        else:
            dir_path = os.path.join(base_path, app_name)
    else:  # macOS, Linux
        base_path = os.path.expanduser('~')
        dir_path = os.path.join(base_path, ".config", app_name)

    # Ensure directory exists
    try:
        os.makedirs(dir_path, exist_ok=True)
        # Keine Ausgabe hier - läuft im Hintergrund
    except OSError as e:
        # Nur bei Debug ausgeben
        try:
            from debug_logger import get_debug_logger
            debug = get_debug_logger()
            if debug and debug.enabled:
                print(f"Warning: Could not create settings directory {dir_path}: {e}")
        except:
            pass
        return filename
    return os.path.join(dir_path, filename)

# --- Standardeinstellungen ---
DEFAULT_SETTINGS = {
    "gemini_api_key": "",  # Must be set by user in settings
    "gemini_model": "gemini-2.5-flash",
    "system_prompt": "Verbessere diesen Text grammatikalisch und stilistisch, behalte aber die ursprüngliche Bedeutung und den Stil bei. Gib mir nur den verbesserten Text wieder, sonst nichts:",
    "hotkey": "<ctrl>+r",
    "text_insert_method": "typed",  # "typed" oder "clipboard"
    "auto_insert_text": True,  # True = automatisch einfügen, False = nur in Zwischenablage
    "debug_enabled": False,
    "debug_log_to_file": False,
}

SETTINGS_FILE = get_appdata_path()

# --- Konfigurationsmanager ---
class ConfigManager:
    """Manages loading and saving application settings."""
    def __init__(self, filename=SETTINGS_FILE, defaults=DEFAULT_SETTINGS):
        self.filename = filename
        self.defaults = defaults
        self.settings = self.load_settings()

    def load_settings(self):
        """Loads settings from the JSON file or returns defaults."""
        settings = self.defaults.copy()
        try:
            if os.path.exists(self.filename):
                # Keine Ausgabe - läuft im Hintergrund
                with open(self.filename, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    settings.update(loaded_settings)
            else:
                # Keine Ausgabe - läuft im Hintergrund
                pass

            # Ensure correct types after loading/updating
            for key in ['auto_insert_text', 'debug_enabled', 'debug_log_to_file']:
                if key in settings:
                    settings[key] = bool(settings[key])

        except (json.JSONDecodeError, IOError, TypeError, ValueError) as e:
            # Nur bei Debug ausgeben
            try:
                from debug_logger import get_debug_logger
                debug = get_debug_logger()
                if debug and debug.enabled:
                    print(f"Error loading settings from {self.filename}: {e}. Using default settings.")
            except:
                pass
            settings = self.defaults.copy()

        return settings

    def save_settings(self):
        """Saves the current settings to the JSON file."""
        try:
            dir_path = os.path.dirname(self.filename)
            if dir_path and not os.path.exists(dir_path):
                try:
                    os.makedirs(dir_path, exist_ok=True)
                    # Keine Ausgabe - läuft im Hintergrund
                except OSError as e:
                    # Nur bei Debug ausgeben
                    try:
                        from debug_logger import get_debug_logger
                        debug = get_debug_logger()
                        if debug and debug.enabled:
                            print(f"Warning: Could not create settings directory {dir_path} on save: {e}")
                    except:
                        pass

            # Keine Ausgabe - läuft im Hintergrund
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4)
        except IOError as e:
            # Nur bei Debug ausgeben
            try:
                from debug_logger import get_debug_logger
                debug = get_debug_logger()
                if debug and debug.enabled:
                    print(f"Error saving settings to {self.filename}: {e}")
            except:
                pass
        except Exception as e:
            # Nur bei Debug ausgeben
            try:
                from debug_logger import get_debug_logger
                debug = get_debug_logger()
                if debug and debug.enabled:
                    print(f"Unexpected error saving settings: {e}")
            except:
                pass

    def get(self, key, default=None):
        """Gets a specific setting value."""
        if default is not None:
            return self.settings.get(key, default)
        return self.settings.get(key, self.defaults.get(key))

    def set(self, key, value):
        """Sets a specific setting value."""
        self.settings[key] = value

