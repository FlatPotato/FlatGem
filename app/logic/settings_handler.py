# app/logic/settings_handler.py
# This file handles saving and loading application settings.

import os
import json
from PySide6.QtCore import QStandardPaths

class SettingsHandler:
    """
    Manages reading and writing all application settings to a JSON file
    in a standard, cross-platform location.
    """
    def __init__(self, app_name="FlatGem"):
        self.config_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation)
        self.app_config_dir = os.path.join(self.config_path, app_name)
        self.settings_file = os.path.join(self.app_config_dir, "settings.json")
        self._create_config_dir_if_not_exists()

    def _create_config_dir_if_not_exists(self):
        """Creates the application's config directory if it's missing."""
        if not os.path.exists(self.app_config_dir):
            try:
                os.makedirs(self.app_config_dir)
            except OSError as e:
                print(f"Error creating config directory: {e}")

    def _load_all_settings(self) -> dict:
        """Loads the entire settings dictionary from the file."""
        if not os.path.exists(self.settings_file):
            return {}
        try:
            with open(self.settings_file, 'r') as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading settings file: {e}")
            return {}

    def _save_all_settings(self, settings: dict):
        """Saves the entire settings dictionary to the file."""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=4)
        except IOError as e:
            print(f"Error saving settings: {e}")

    def save_api_key(self, api_key: str):
        """Saves only the API key, preserving other settings."""
        settings = self._load_all_settings()
        settings["api_key"] = api_key
        self._save_all_settings(settings)
        print(f"API key saved to {self.settings_file}")

    def load_api_key(self) -> str | None:
        """Loads only the API key from the settings."""
        settings = self._load_all_settings()
        api_key = settings.get("api_key")
        if api_key: print("API key loaded from settings.")
        return api_key

    def save_main_window_state(self, state: dict):
        """Saves the state of the main window."""
        settings = self._load_all_settings()
        # We update the settings dictionary with the new state
        settings.update(state)
        self._save_all_settings(settings)
        print("Main window state saved.")

    def load_main_window_state(self) -> dict:
        """Loads the state of the main window."""
        settings = self._load_all_settings()
        # We don't need to return the api_key here
        settings.pop("api_key", None)
        print("Main window state loaded.")
        return settings