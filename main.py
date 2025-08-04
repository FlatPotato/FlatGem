# main.py
# The main entry point and controller for the FlatGem application.

import sys
import os
import requests
from packaging.version import parse as parse_version
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QFile, QTextStream, QThread, Signal, QObject, QUrl
from PySide6.QtGui import QFontDatabase, QIcon, QDesktopServices
import ctypes

from app.logic.settings_handler import SettingsHandler
from app.logic.api_handler import GeminiAPIHandler
from app.views.welcome_window import WelcomeWindow
from app.views.main_window import MainWindow

# 1. CURRENT PROGRAM VERSION
# Before compiling a new .exe file, just increment this number.
# For example, "1.0.0" -> "1.0.1" or "1.1.0".
CURRENT_VERSION = "1.0.0"

# 2. LINK TO YOUR version.json
# Paste the "Raw" link to your version.json file from GitHub Gist here.
# The program will use this link to find out what the latest version is.
VERSION_INFO_URL = "https://gist.githubusercontent.com/FlatPotato/844cfcc9d837131604d23fb304f33fdb/raw/a39faf71567c97f1ef2bfcd072dc8ace91ab4073/flatgem_version.json" # REPLACE WITH YOUR LINK

# 3. LINK TO THE STORE PAGE
# The link that will open for the user when they click "Update".
# It should lead to the page where they MADE THE PURCHASE (Itch.io, Gumroad),
# so they can log into their account and download the new version.
STORE_PAGE_URL = "https://flatpotato22.itch.io/flatgem" # REPLACE WITH YOUR LINK


# --- This is the update check mechanism itself. It runs in the background. ---
class UpdateChecker(QObject):
    """
    A worker that checks for updates in a separate thread.
    It does not interfere with the program's launch.
    """
    # A signal that is emitted if a new version is found.
    # It passes the new version number (str) and its release notes (str).
    update_found = Signal(str, str)

    def run(self):
        """Downloads the info file and compares versions."""
        try:
            # For debugging, so you can see in the console that the check has started.
            print(f"Checking for updates... Current version: {CURRENT_VERSION}")

            # We make an internet request to your link. 5-second timeout.
            response = requests.get(VERSION_INFO_URL, timeout=5)
            response.raise_for_status()  # If the site doesn't respond, it will raise an error

            # Convert the response text into a format Python can understand
            data = response.json()
            latest_version_str = data.get("version", "0.0.0")

            print(f"Latest version found online: {latest_version_str}")

            # Compare versions. 'packaging.version' can correctly compare
            # "1.10.0" and "1.9.0", unlike simple string comparison.
            if parse_version(latest_version_str) > parse_version(CURRENT_VERSION):
                print(f"Newer version found: {latest_version_str}. Notifying user.")
                notes = data.get("notes", "No release notes provided.")
                # Send a signal to the main controller that it's time to show the dialog.
                self.update_found.emit(latest_version_str, notes)

        # This block will execute if the user has no internet or GitHub Gist is down.
        # The program will not crash but will simply skip the check.
        except requests.exceptions.RequestException as e:
            print(f"Update check failed: Could not connect. {e}")
        except Exception as e:
            print(f"An unexpected error occurred during update check: {e}")


# --- The main conductor of the entire application ---
class ApplicationController:
    """
    The main controller. It starts all processes, including the update check.
    """
    def __init__(self, app):
        self.app = app
        self.settings_handler = SettingsHandler()
        self.welcome_window = None
        self.main_window = None
        self.last_window_center = None

        # --- Setting up the thread for update checking ---
        # 1. Create a separate "conveyor" (thread) to avoid freezing the main one.
        self.update_thread = QThread()
        # 2. Create our "worker".
        self.update_checker = UpdateChecker()
        # 3. Move the "worker" to the "thread".
        self.update_checker.moveToThread(self.update_thread)
        # 4. We say: "When the worker emits the 'update_found' signal, call the 'show_update_dialog' function".
        self.update_checker.update_found.connect(self.show_update_dialog)
        # 5. We say: "When the thread starts, let the worker start its job (call its run function)".
        self.update_thread.started.connect(self.update_checker.run)

    def run(self):
        """Starts the application and the update check."""
        # Give the command to "start the thread". The check will run in the background.
        self.update_thread.start()

        saved_key = self.settings_handler.load_api_key()
        self.show_welcome_window(saved_key)

    def show_update_dialog(self, version, notes):
        """This function is called by a signal and shows the user the update window."""
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Update Available")
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setText(f"A new version ({version}) of FlatGem is available!")
        # Format the notes to make them look nice.
        msg_box.setInformativeText(f"<b>What's new:</b>\n{notes}")

        # Add buttons
        update_button = msg_box.addButton("Go to Download Page", QMessageBox.ButtonRole.AcceptRole)
        later_button = msg_box.addButton("Later", QMessageBox.ButtonRole.RejectRole)

        msg_box.exec()

        # If the user clicked the "Update" button, open the store link.
        if msg_box.clickedButton() == update_button:
            QDesktopServices.openUrl(QUrl(STORE_PAGE_URL))

        # After the dialog has been shown, we no longer need the thread. Shut it down.
        self.update_thread.quit()
        self.update_thread.wait()

    # --- Rest of the controller code without changes ---
    def show_welcome_window(self, saved_key: str | None = None):
        self.welcome_window = WelcomeWindow(saved_key=saved_key)
        if self.last_window_center:
            new_geo = self.welcome_window.geometry()
            new_geo.moveCenter(self.last_window_center)
            self.welcome_window.setGeometry(new_geo)
        self.welcome_window.api_key_submitted.connect(self.handle_api_key_submission)
        self.welcome_window.show()

    def show_main_window(self, api_key: str, models_list: list[str]):
        saved_state = self.settings_handler.load_main_window_state()
        self.main_window = MainWindow(models_list=models_list, saved_state=saved_state)
        if self.last_window_center:
            new_geo = self.main_window.geometry()
            new_geo.moveCenter(self.last_window_center)
            self.main_window.setGeometry(new_geo)
        self.main_window.load_api_key_and_configure(api_key, models_list)
        self.main_window.change_api_key_requested.connect(self.handle_change_api_key_request)
        self.main_window.closing.connect(self.handle_main_window_close)
        self.main_window.show()
        if self.welcome_window:
            self.welcome_window.close()

    def handle_api_key_submission(self, api_key: str):
        if self.welcome_window:
            self.last_window_center = self.welcome_window.geometry().center()

        # Key is now confirmed valid, so we configure the main handler and save the key
        self.settings_handler.save_api_key(api_key)
        GeminiAPIHandler(api_key) # Configure the main process with the valid key
        models = GeminiAPIHandler.get_available_models() # Now we can safely get models

        self.show_main_window(api_key, models)

    def handle_change_api_key_request(self):
        if self.main_window:
            self.last_window_center = self.main_window.geometry().center()
            self.main_window.close()
        # This correctly re-runs the application logic from the start,
        # including loading any saved keys.
        self.run()

    def handle_main_window_close(self, current_state: dict):
        self.settings_handler.save_main_window_state(current_state)
        # If the thread is still running, shut it down when the program closes.
        if self.update_thread.isRunning():
            self.update_thread.quit()
            self.update_thread.wait()


def main():
    """
    The main function to initialize and run the application.
    """
    app = QApplication(sys.argv)
    script_dir = os.path.dirname(os.path.abspath(__file__))

    if sys.platform == 'win32':
        myappid = 'flatpotato.flatgem.1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        print(f"Windows AppUserModelID set to: {myappid}")

    icon_path = os.path.join(script_dir, "assets", "icons", "flatgemlogo.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
        print("Application icon loaded successfully.")
    else:
        print(f"Warning: Application icon not found at '{icon_path}'.")

    font_path = os.path.join(script_dir, "assets", "fonts", "Roboto-Regular.ttf")
    font_id = QFontDatabase.addApplicationFont(font_path)
    if font_id != -1:
        font_families = QFontDatabase.applicationFontFamilies(font_id)
        if font_families:
            print(f"Successfully loaded font: '{font_families[0]}'")
    else:
        print(f"Warning: Failed to load font at '{font_path}'.")

    try:
        stylesheet_path = os.path.join(script_dir, "styles", "dark_theme.qss")
        style_file = QFile(stylesheet_path)
        if style_file.open(QFile.OpenModeFlag.ReadOnly | QFile.OpenModeFlag.Text):
            stream = QTextStream(style_file)
            app.setStyleSheet(stream.readAll())
            print("Stylesheet loaded successfully.")
    except Exception as e:
        print(f"An error occurred while loading the stylesheet: {e}")

    controller = ApplicationController(app)
    controller.run()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()