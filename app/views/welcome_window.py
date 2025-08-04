# app/views/welcome_window.py
# This file defines the UI and logic for the welcome screen. (Simplified version)

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QFont

# We no longer import anything from api_handler for validation.
# The validation is now fully self-contained in the thread.

class ApiKeyValidator(QThread):
    """
    A worker thread that validates the API key in a completely isolated environment.
    It has only two outcomes: valid or invalid.
    """
    # Signal emits a boolean: True if valid, False if invalid.
    validation_finished = Signal(bool)

    def __init__(self, api_key):
        super().__init__()
        self.api_key = api_key.strip() # Sanitize the key immediately.

    def run(self):
        """
        The function that will be executed in the separate thread.
        All imports and library calls are contained here. If the thread
        crashes or the library state gets "poisoned", it does not affect
        the main application.
        """
        try:
            # Import the library ONLY inside the thread.
            import google.generativeai as genai

            if not self.api_key:
                self.validation_finished.emit(False)
                return

            # This is the dangerous call. It happens in isolation.
            genai.configure(api_key=self.api_key)

            # A simple, low-cost operation to test the key.
            genai.GenerativeModel('gemini-2.5-flash').count_tokens("test")

            # If we reached here, the key is valid.
            self.validation_finished.emit(True)

        except Exception:
            # ANY exception (invalid key, no internet, C++ error, etc.)
            # means the key is not usable. The outcome is the same: INVALID.
            self.validation_finished.emit(False)


class WelcomeWindow(QMainWindow):
    """
    The first window the user sees. It emits a signal
    when the user submits a valid key.
    """
    api_key_submitted = Signal(str)

    def __init__(self, saved_key: str | None = None):
        super().__init__()
        self.setWindowTitle("Welcome to FlatGem")
        self.setFixedSize(500, 420)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(25, 20, 25, 20)
        main_layout.setSpacing(15)

        # --- UI ELEMENTS (No changes) ---
        title_area_layout = QVBoxLayout(); title_area_layout.setSpacing(0)
        title_label = QLabel("FlatGem"); title_label.setObjectName("TitleLabel"); title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        author_label = QLabel("by FlatPotato"); author_font = QFont(); author_font.setPointSize(11); author_label.setFont(author_font); author_label.setAlignment(Qt.AlignmentFlag.AlignCenter); author_label.setStyleSheet("color: #aaa;"); author_label.setContentsMargins(0, 0, 0, 10)
        title_area_layout.addWidget(title_label); title_area_layout.addWidget(author_label)
        info_label = QLabel("To get started, you need a free Google Gemini API key.\nPaste your key below."); info_label.setAlignment(Qt.AlignmentFlag.AlignCenter); info_label.setWordWrap(True)
        self.api_key_input = QLineEdit(); self.api_key_input.setPlaceholderText("Enter your Gemini API key here"); self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        get_key_label = QLabel('<a href="https://aistudio.google.com/app/apikey" style="color: #009cff;">Get your API Key from Google AI Studio</a>'); get_key_label.setOpenExternalLinks(True); get_key_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label = QLabel("Enter an API key to begin."); self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        button_layout = QHBoxLayout(); button_layout.setSpacing(10)
        self.continue_button = QPushButton("Continue"); self.continue_button.setObjectName("PrimaryButton"); self.continue_button.setEnabled(False)
        button_layout.addWidget(self.continue_button)
        main_layout.addLayout(title_area_layout); main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)); main_layout.addWidget(info_label); main_layout.addWidget(self.api_key_input); main_layout.addWidget(get_key_label); main_layout.addWidget(self.status_label); main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)); main_layout.addLayout(button_layout)


        # --- SIMPLIFIED VALIDATION MECHANISM ---
        self.validator_thread = None
        self.debounce_timer = QTimer(self)
        self.debounce_timer.setInterval(750) # 750ms delay after user stops typing.
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self.start_validation)

        self.api_key_input.textChanged.connect(self.on_text_changed)
        self.continue_button.clicked.connect(self.submit_and_finish)

        if saved_key:
            self.api_key_input.setText(saved_key)
            self.start_validation() # Automatically validate saved key on startup

    def on_text_changed(self):
        """Reset status and start the countdown to validate."""
        self.continue_button.setEnabled(False)
        self.status_label.setText("...")
        self.status_label.setStyleSheet("color: #c5c5d4;")
        self.debounce_timer.start()

    def start_validation(self):
        """The robust way to start the validation thread."""
        # If a thread is already running, do nothing. Wait for it to finish.
        if self.validator_thread and self.validator_thread.isRunning():
            return

        api_key = self.api_key_input.text()
        if not api_key.strip():
            self.status_label.setText("Enter an API key to begin.")
            self.status_label.setStyleSheet("color: #c5c5d4;")
            return

        # State 1: CHECKING
        self.status_label.setText("Checking key...")
        self.status_label.setStyleSheet("color: #c5c5d4;")
        self.continue_button.setEnabled(False)

        # Start a new, clean validation thread.
        self.validator_thread = ApiKeyValidator(api_key)
        self.validator_thread.validation_finished.connect(self.on_validation_finished)
        self.validator_thread.start()

    def on_validation_finished(self, is_valid: bool):
        """
        Called when the validation thread is done.
        Handles the two possible outcomes: valid or invalid.
        """
        # Ignore result if user has changed the text in the meantime.
        if self.api_key_input.text().strip() != self.validator_thread.api_key:
            return

        if is_valid:
            # State 2: VALID
            self.status_label.setText("✅ API Key is valid!")
            self.status_label.setStyleSheet("color: #2ecc71;") # Green
            self.continue_button.setEnabled(True)
        else:
            # State 3: INVALID
            self.status_label.setText("❌ Invalid API Key.")
            self.status_label.setStyleSheet("color: #e74c3c;") # Red
            self.continue_button.setEnabled(False)

    def submit_and_finish(self):
        """Emits the signal with the API key."""
        self.api_key_submitted.emit(self.api_key_input.text())