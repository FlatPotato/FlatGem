# app/views/main_window.py
# This file defines the UI for the main application window.

import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QFileDialog, QSizePolicy, QSpacerItem,
    QStyle, QFrame, QMessageBox, QTextEdit, QMenu, QComboBox, QProgressBar,
    QSpinBox, QDialog, QDialogButtonBox, QTabWidget
)
from PySide6.QtCore import Qt, Signal, QUrl, QThread, QTimer, QSize
from PySide6.QtGui import QAction, QDesktopServices, QPixmap, QIcon

from .bouncy_checkbox import BouncyCheckBox
from ..logic.file_processor import FileProcessor
from .static_icon_button import StaticIconButton

MODEL_HINTS = {
    "pro":   {"icon": "🧠", "category": "High Quality"},
    "flash": {"icon": "⚡️", "category": "Speed & Efficiency"},
    "gemma": {"icon": "⚙️", "category": "Compact & Fast"}
}
# --- UPDATED: URL for your page ---
CONTACT_URL = "https://flatpotato22.itch.io/"

# --- ADDED: Custom ComboBox to ignore wheel events ---
class NoScrollComboBox(QComboBox):
    """
    A custom QComboBox that ignores mouse wheel events, allowing them
    to be processed by parent widgets (e.g., a QScrollArea).
    """
    def wheelEvent(self, event):
        """
        Overrides the default wheel event handler.
        By ignoring the event, we prevent the combo box from changing its value
        and allow the event to propagate to the parent for scrolling.
        """
        event.ignore()

class DonationDialog(QDialog):
    """
    A custom dialog window for cryptocurrency donations.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Support FlatGem")
        self.setMinimumWidth(550)

        main_layout = QVBoxLayout(self)

        info_label = QLabel(
            "Enjoying the app? It's built by an indie developer. Support my work with a crypto donation.\n"
            "I prefer crypto to avoid taxes and KYC, so 100% of your support goes directly to the creator. Thanks for your support! :D"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("font-size: 10pt; color: #c5c5d4;")
        main_layout.addWidget(info_label)

        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)

        # --- Wallet Addresses ---
        # TODO: Replace these placeholder addresses with your actual wallet addresses.
        wallets = {
            "BTC": ("bc1qlaptx3uvyzs83dejakdq647nn82qqwd3t3w97l", "Bitcoin (BTC)"),
            "ETH": ("0xc395bD0E7e257835b03D62195f08980cCB3bcC27", "Ethereum (ETH)"),
            "USDT": ("0xc395bD0E7e257835b03D62195f08980cCB3bcC27", "USDT (TRON/TRC-20 Network)"),
            "XMR": ("87eiGmif2YALvTD73xaEhs8jyrnFWv5zWL9sd8mXUofQaUBpBwKyx96gveptbyzX9cHe2Wxh62ur6LGUiZQwgAR8SJco3HS", "Monero (XMR)")
        }

        for currency, (address, name) in wallets.items():
            script_dir = os.path.dirname(os.path.abspath(__file__))
            qr_path = os.path.join(script_dir, "..", "..", "assets", "icons", f"{currency.lower()}_qr.png")

            tab = self.create_crypto_tab(name, address, qr_path)
            tab_widget.addTab(tab, currency)

        close_button = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_button.rejected.connect(self.reject)
        main_layout.addWidget(close_button)

    def create_crypto_tab(self, name: str, address: str, qr_code_path: str) -> QWidget:
        tab_widget = QWidget()
        layout = QHBoxLayout(tab_widget)
        layout.setSpacing(20)

        # QR Code
        qr_label = QLabel()
        qr_label.setFixedSize(160, 160)
        qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = QPixmap(qr_code_path)
        if pixmap.isNull():
            qr_label.setText(f"QR Code for\n{name}\nnot found.")
            qr_label.setStyleSheet("border: 1px dashed #4f5263; border-radius: 8px;")
            print(f"Warning: QR Code image not found at '{qr_code_path}'")
        else:
            qr_label.setPixmap(pixmap.scaled(
                qr_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation
            ))
        layout.addWidget(qr_label)

        # Address Info
        address_layout = QVBoxLayout()
        address_layout.addStretch()

        address_title_label = QLabel(f"<b>{name} Address:</b>")

        address_edit = QLineEdit(address)
        address_edit.setReadOnly(True)
        address_edit.setStyleSheet("font-size: 10pt;")

        copy_button = QPushButton("Copy Address")
        copy_button.clicked.connect(lambda: self.copy_to_clipboard(address, copy_button))

        address_layout.addWidget(address_title_label)
        address_layout.addWidget(address_edit)
        address_layout.addWidget(copy_button)
        address_layout.addStretch()

        layout.addLayout(address_layout)
        return tab_widget

    def copy_to_clipboard(self, address: str, button: QPushButton):
        QApplication.clipboard().setText(address)
        print(f"Copied to clipboard: {address}")
        button.setText("Copied!")
        QTimer.singleShot(2000, lambda: button.setText("Copy Address"))


class ErrorLogDialog(QDialog):
    def __init__(self, errors: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Error Log")
        self.setMinimumSize(700, 400)

        layout = QVBoxLayout(self)

        info_label = QLabel("The following errors occurred during processing:")
        info_label.setStyleSheet("font-weight: bold;")

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setText("\n\n".join(errors))

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)

        layout.addWidget(info_label)
        layout.addWidget(self.log_view)
        layout.addWidget(button_box)

        self.log_view.setStyleSheet("background-color: #21232c; border: 1px solid #4f5263; padding: 8px; border-radius: 8px; color: #e6e7f0;")


class MainWindow(QMainWindow):
    change_api_key_requested = Signal()
    closing = Signal(dict)

    def __init__(self, models_list: list[str] = None, saved_state: dict = None):
        super().__init__()
        self.setWindowTitle("FlatGem")
        self.resize(800, 650)

        self.processing_thread = None
        self.file_processor = None
        self.api_key = None

        scroll_area = QScrollArea(); scroll_area.setWidgetResizable(True); scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff); self.setCentralWidget(scroll_area)
        main_widget = QWidget(); scroll_area.setWidget(main_widget)
        main_layout = QVBoxLayout(main_widget); main_layout.setContentsMargins(20, 15, 20, 15); main_layout.setSpacing(15)

        # --- PROMPT SECTION ---
        prompt_title = QLabel("System Prompt"); prompt_title.setStyleSheet("font-size: 13pt; font-weight: bold;")
        self.prompt_edit = QTextEdit(); self.prompt_edit.setPlaceholderText("Enter your detailed instructions for the AI here. The quality and detail of the system prompt directly influence the quality of the output. Before processing all the files, first process one or two files as a test. Wait for confirmation that the output is correct before proceeding with the rest. This ensures the AI has correctly understood the task. I also recommend that you ask the AI not to use Markdown formatting in its output."); self.prompt_edit.setMinimumHeight(150)

        prompt_buttons_layout = QHBoxLayout()
        self.generate_btn = QPushButton("Generate with AI"); self.generate_btn.setObjectName("UtilityButton")
        self.tips_btn = QPushButton("Prompting Tips"); self.tips_btn.setObjectName("UtilityButton")

        self.about_btn = QPushButton("About FlatPotato"); self.about_btn.setObjectName("UtilityButton")

        # --- FIX: Use the new StaticIconButton ---
        self.donate_btn = StaticIconButton("Donate")
        self.donate_btn.setObjectName("DonateButton") # Set object name for QSS
        script_dir = os.path.dirname(__file__)
        icon_path = os.path.join(script_dir, '..', '..', 'assets', 'icons', 'gift.svg')
        self.donate_btn.setIcon(QIcon(icon_path))
        self.donate_btn.setIconSize(QSize(16, 16))
        # --- END FIX ---

        prompt_buttons_layout.addWidget(self.generate_btn)
        prompt_buttons_layout.addWidget(self.tips_btn)
        prompt_buttons_layout.addWidget(self.about_btn)
        prompt_buttons_layout.addWidget(self.donate_btn)
        prompt_buttons_layout.addStretch()

        self.generate_btn.clicked.connect(self.open_ai_studio)
        self.tips_btn.clicked.connect(self.show_prompting_tips)
        self.about_btn.clicked.connect(self.open_about_page)
        self.donate_btn.clicked.connect(self.open_donation_dialog)

        main_layout.addWidget(prompt_title)
        main_layout.addWidget(self.prompt_edit)
        main_layout.addLayout(prompt_buttons_layout)

        # --- PROCESSING CONTROLS ---
        self.start_button = QPushButton("Start Processing"); self.start_button.setObjectName("PrimaryButton")
        self.pause_button = QPushButton("Pause"); self.pause_button.setVisible(False); self.pause_button.setCheckable(True)
        self.stop_button = QPushButton("Stop"); self.stop_button.setVisible(False); self.stop_button.setObjectName("StopButton")
        processing_buttons_layout = QHBoxLayout(); processing_buttons_layout.addStretch(); processing_buttons_layout.addWidget(self.start_button); processing_buttons_layout.addWidget(self.pause_button); processing_buttons_layout.addWidget(self.stop_button)

        self.progress_widget = QWidget(); self.progress_widget.setVisible(False)
        progress_layout = QVBoxLayout(self.progress_widget); progress_layout.setContentsMargins(0, 10, 0, 0)
        self.progress_label = QLabel("Processed 0 of 0 files"); self.progress_bar = QProgressBar(); self.progress_bar.setTextVisible(False)
        self.current_file_label = QLabel("Currently processing: -"); self.current_file_label.setStyleSheet("font-size: 9pt; color: #c5c5d4;")
        progress_layout.addWidget(self.progress_label); progress_layout.addWidget(self.progress_bar); progress_layout.addWidget(self.current_file_label)

        main_layout.addLayout(processing_buttons_layout)
        main_layout.addWidget(self.progress_widget)
        main_layout.addWidget(self.create_separator())

        # --- PROCESSING SETTINGS SECTION ---
        processing_settings_title = QLabel("Processing Settings"); processing_settings_title.setStyleSheet("font-size: 13pt; font-weight: bold;")
        main_layout.addWidget(processing_settings_title)
        main_layout.addSpacing(5)

        ext_layout = QHBoxLayout()
        output_ext_label = QLabel("Output File Extension")
        self.output_ext_edit = QLineEdit()
        self.output_ext_edit.setPlaceholderText("e.g., .json")
        self.output_ext_edit.setFixedWidth(150)
        ext_layout.addWidget(output_ext_label)
        ext_layout.addWidget(self.output_ext_edit)
        ext_layout.addStretch()
        main_layout.addLayout(ext_layout)

        output_ext_desc = QLabel("Leave empty to keep original extension. Ensure your prompt instructs the AI to generate content in the correct format.")
        output_ext_desc.setStyleSheet("color: #c5c5d4; font-size: 9pt;"); output_ext_desc.setWordWrap(True)
        main_layout.addWidget(output_ext_desc); main_layout.addSpacing(15)

        delay_layout = QHBoxLayout()
        delay_label = QLabel("Delay Between Files (seconds)")
        self.delay_spinbox = QSpinBox()
        self.delay_spinbox.setRange(0, 300); self.delay_spinbox.setValue(10); self.delay_spinbox.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons); self.delay_spinbox.setSuffix(" s")
        self.delay_spinbox.setFixedWidth(150)
        delay_layout.addWidget(delay_label)
        delay_layout.addWidget(self.delay_spinbox)
        delay_layout.addStretch()
        main_layout.addLayout(delay_layout)

        delay_desc = QLabel("Google's API has a requests per minute (RPM) limit. A delay prevents errors on the free plan. Recommended: 10s for large batches.")
        delay_desc.setStyleSheet("color: #c5c5d4; font-size: 9pt;"); delay_desc.setWordWrap(True)
        main_layout.addWidget(delay_desc)
        main_layout.addSpacing(15)

        self.subfolders_checkbox = BouncyCheckBox("Process Subfolders")
        main_layout.addWidget(self.subfolders_checkbox)
        subfolders_desc = QLabel("If checked, the application will recursively scan the input folder and recreate the folder structure in the output directory.")
        subfolders_desc.setStyleSheet("color: #c5c5d4; font-size: 9pt;"); subfolders_desc.setWordWrap(True)
        main_layout.addWidget(subfolders_desc)

        main_layout.addWidget(self.create_separator())

        # --- FOLDER SETTINGS ---
        folder_title = QLabel("Folder Settings"); folder_title.setStyleSheet("font-size: 13pt; font-weight: bold;"); main_layout.addWidget(folder_title)
        input_label = QLabel("Select the folder with files to process."); self.input_path_edit = QLineEdit(); self.input_path_edit.setPlaceholderText("e.g., C:/Users/YourName/Documents/Project/Input_Folder"); self.input_browse_btn = QPushButton(); self.input_browse_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)); self.input_browse_btn.clicked.connect(self.browse_for_input_folder); input_layout = QHBoxLayout(); input_layout.addWidget(self.input_path_edit); input_layout.addWidget(self.input_browse_btn); output_label = QLabel("Select a folder to save processed files."); self.output_path_edit = QLineEdit(); self.output_path_edit.setPlaceholderText("e.g., C:/Users/YourName/Documents/Project/Output_Folder"); self.output_browse_btn = QPushButton(); self.output_browse_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)); self.output_browse_btn.clicked.connect(self.browse_for_output_folder); output_layout = QHBoxLayout(); output_layout.addWidget(self.output_path_edit); output_layout.addWidget(self.output_browse_btn); main_layout.addWidget(input_label); main_layout.addLayout(input_layout); main_layout.addSpacing(10); main_layout.addWidget(output_label); main_layout.addLayout(output_layout); main_layout.addWidget(self.create_separator());

        # --- MODEL SETTINGS ---
        model_title = QLabel("Model Settings"); model_title.setStyleSheet("font-size: 13pt; font-weight: bold;"); main_layout.addWidget(model_title)
        model_label = QLabel("Choose the AI model.");

        self.model_combo = NoScrollComboBox()

        self.populate_models_combo(models_list if models_list else []);
        main_layout.addWidget(model_label); main_layout.addWidget(self.model_combo)
        model_desc = QLabel("I recommend using the gemini-2.5-flash model. It's free and works well. Be careful, some models on this list might behave strangely. \nWhen selecting a Gemini model, consider its specific strengths and API limits. A less capable model may not perform your task adequately, while a more powerful one could quickly deplete your daily API quota."); model_desc.setStyleSheet("color: #c5c5d4; font-size: 9pt;"); model_desc.setWordWrap(True); main_layout.addWidget(model_desc)
        model_link_label = QLabel('<a href="https://ai.google.dev/models/gemini" style="color: #009cff;">Learn about models...</a>'); model_link_label.setOpenExternalLinks(True); main_layout.addSpacing(4); main_layout.addWidget(model_link_label); main_layout.addSpacing(15);
        self.thinking_mode_checkbox = BouncyCheckBox("Thinking Mode"); thinking_desc = QLabel("Allows the model to perform more complex reasoning before giving an answer."); thinking_desc.setStyleSheet("color: #c5c5d4; font-size: 9pt;"); thinking_desc.setWordWrap(True); main_layout.addWidget(self.thinking_mode_checkbox); main_layout.addWidget(thinking_desc); main_layout.addSpacing(10);
        main_layout.addStretch();

        # --- BOTTOM BUTTONS ---
        bottom_button_layout = QHBoxLayout(); self.change_api_key_btn = QPushButton("Change API Key"); self.change_api_key_btn.clicked.connect(self.change_api_key_requested); self.reset_settings_btn = QPushButton("Reset Settings"); self.reset_settings_btn.clicked.connect(self.confirm_reset_settings); bottom_button_layout.addWidget(self.change_api_key_btn); bottom_button_layout.addWidget(self.reset_settings_btn); bottom_button_layout.addStretch(); main_layout.addLayout(bottom_button_layout)

        self.settings_widgets = [self.prompt_edit, self.generate_btn, self.tips_btn, self.about_btn, self.donate_btn, self.output_ext_edit, self.delay_spinbox, self.subfolders_checkbox, self.input_path_edit, self.output_path_edit, self.input_browse_btn, self.output_browse_btn, self.model_combo, self.thinking_mode_checkbox, self.change_api_key_btn, self.reset_settings_btn]

        self.start_button.clicked.connect(self.start_processing_confirmation); self.stop_button.clicked.connect(self.stop_processing); self.pause_button.toggled.connect(self.toggle_pause_processing); self.input_path_edit.textChanged.connect(self._update_start_button_state); self.output_path_edit.textChanged.connect(self._update_start_button_state); self.prompt_edit.textChanged.connect(self._update_start_button_state)
        self._update_start_button_state()
        if saved_state: self.apply_state(saved_state)

    def open_donation_dialog(self):
        dialog = DonationDialog(self)
        dialog.exec()

    def open_about_page(self):
        QDesktopServices.openUrl(QUrl(CONTACT_URL))

    def start_processing_confirmation(self):
        input_path = self.input_path_edit.text(); output_path = self.output_path_edit.text()
        if input_path and output_path:
            norm_input_path = os.path.abspath(input_path)
            norm_output_path = os.path.abspath(output_path)
            if norm_input_path == norm_output_path:
                QMessageBox.critical(self, "Path Error", "Critical: The Input and Output folders cannot be the same. This would overwrite your original files.\n\nPlease choose a different folder for the output."); return
        report = FileProcessor.scan_input_folder(input_path, output_path, self.subfolders_checkbox.isChecked())
        if report["files_found"] == 0: QMessageBox.warning(self, "No Files Found", "The selected input folder contains no files. Please select a different folder."); return
        if report["warnings"]:
            warning_text = "Please review the following before starting:\n\n" + "\n".join(report["warnings"])
            msg_box = QMessageBox(self); msg_box.setWindowTitle("Pre-flight Check"); msg_box.setText(warning_text); msg_box.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel); msg_box.setDefaultButton(QMessageBox.StandardButton.Ok); msg_box.setIcon(QMessageBox.Icon.Information)
            if msg_box.exec() != QMessageBox.StandardButton.Ok: return
        self.start_processing()

    def start_processing(self):
        self._set_controls_enabled(False); self.start_button.setVisible(False); self.pause_button.setVisible(True); self.stop_button.setVisible(True); self.progress_widget.setVisible(True)
        settings = self.get_current_state(); settings["api_key"] = self.api_key
        self.file_processor = FileProcessor(settings)
        self.processing_thread = QThread(); self.file_processor.moveToThread(self.processing_thread)
        self.file_processor.progress_updated.connect(self.update_progress)
        self.file_processor.processing_finished.connect(self.on_processing_finished)
        self.processing_thread.started.connect(self.file_processor.run)
        self.processing_thread.start()

    def stop_processing(self):
        if self.file_processor: self.file_processor.stop()
        if self.processing_thread: self.processing_thread.quit(); self.processing_thread.wait()
        self._set_controls_enabled(True); self.start_button.setVisible(True); self.pause_button.setVisible(False); self.pause_button.setChecked(False); self.stop_button.setVisible(False); self.progress_widget.setVisible(False)

    def toggle_pause_processing(self, paused):
        if self.file_processor: self.file_processor.toggle_pause(paused)
        self.pause_button.setText("Resume" if paused else "Pause")

    def update_progress(self, current, total, filename):
        self.progress_bar.setMaximum(total); self.progress_bar.setValue(current); self.progress_label.setText(f"Processed {current} of {total} files"); self.current_file_label.setText(f"Current: {filename}")

    def on_processing_finished(self, message: str, errors: list):
        self.stop_processing()
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Processing Complete"); msg_box.setText(message)
        if errors:
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setInformativeText("Some files could not be processed. Click 'Show Details' for the full error log.")
            show_details_btn = msg_box.addButton("Show Details", QMessageBox.ButtonRole.ActionRole)
            msg_box.addButton(QMessageBox.StandardButton.Ok)
            msg_box.exec()
            if msg_box.clickedButton() == show_details_btn:
                error_dialog = ErrorLogDialog(errors, self); error_dialog.exec()
        else:
            msg_box.setIcon(QMessageBox.Icon.Information); msg_box.exec()

    def get_current_state(self):
        selected_model_text = ""; selected_model_data = ""
        if self.model_combo.count() > 0:
            selected_model_text = self.model_combo.currentText()
            selected_model_data = self.model_combo.currentData()
        state = {
            "prompt_text": self.prompt_edit.toPlainText(), "input_path": self.input_path_edit.text(), "output_path": self.output_path_edit.text(),
            "output_extension": self.output_ext_edit.text(), "processing_delay": self.delay_spinbox.value(), "selected_model_display": selected_model_text,
            "selected_model_name": selected_model_data, "thinking_mode": self.thinking_mode_checkbox.isChecked(), "process_subfolders": self.subfolders_checkbox.isChecked(),
        }
        return state

    def apply_state(self, state):
        self.prompt_edit.setPlainText(state.get("prompt_text", "")); self.input_path_edit.setText(state.get("input_path", "")); self.output_path_edit.setText(state.get("output_path", ""))
        self.output_ext_edit.setText(state.get("output_extension", "")); self.delay_spinbox.setValue(state.get("processing_delay", 10)); self.thinking_mode_checkbox.setChecked(state.get("thinking_mode", False));
        self.subfolders_checkbox.setChecked(state.get("process_subfolders", False))
        model_to_select = state.get("selected_model_display", "")
        if model_to_select:
            for i in range(self.model_combo.count()):
                if self.model_combo.itemText(i) == model_to_select: self.model_combo.setCurrentIndex(i); break
        print("Saved state applied to main window.")

    def closeEvent(self, event):
        print("Main window is closing, emitting state."); current_state = self.get_current_state(); self.closing.emit(current_state); event.accept()

    def open_ai_studio(self): QDesktopServices.openUrl(QUrl("https://aistudio.google.com/prompts/new_chat"))

    def _set_controls_enabled(self, enabled):
        for widget in self.settings_widgets: widget.setEnabled(enabled)

    def _update_start_button_state(self):
        is_ready = bool(self.input_path_edit.text().strip() and self.output_path_edit.text().strip() and self.prompt_edit.toPlainText().strip()); self.start_button.setEnabled(is_ready)

    def create_separator(self):
        separator = QFrame(); separator.setObjectName("Separator"); separator.setFrameShape(QFrame.Shape.HLine); separator.setFrameShadow(QFrame.Shadow.Sunken); return separator

    def show_prompting_tips(self):
        title = "Prompting Tips"
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__)); tips_path = os.path.join(current_dir, "..", "..", "docs", "prompt_tips.txt")
            with open(tips_path, 'r', encoding='utf-8') as f: text = f.read()
            msg_box = QMessageBox(self); msg_box.setWindowTitle(title); msg_box.setText(text); msg_box.setTextFormat(Qt.TextFormat.RichText); msg_box.addButton(QMessageBox.StandardButton.Ok); msg_box.setIcon(QMessageBox.Icon.NoIcon); msg_box.exec()
        except FileNotFoundError: QMessageBox.warning(self, "Error", "Could not find 'prompt_tips.txt'.")
        except Exception as e: QMessageBox.warning(self, "Error", f"An error occurred: {e}")

    def populate_models_combo(self, model_list: list[str]):
        self.model_combo.clear(); default_index = -1
        for i, model_name in enumerate(model_list):
            display_text = model_name
            for key, hints in MODEL_HINTS.items():
                if key in model_name: display_text = f"{hints['icon']} {model_name} ({hints['category']})"; break
            self.model_combo.addItem(display_text, userData=model_name)
            # --- FIX: Look for 2.5 flash as default ---
            if "gemini-2.5-flash" in model_name: default_index = i
        if default_index != -1: self.model_combo.setCurrentIndex(default_index)

    def confirm_reset_settings(self):
        msg_box = QMessageBox(self); msg_box.setWindowTitle("Confirm Reset"); msg_box.setText("Are you sure you want to reset all settings on this page?"); msg_box.setInformativeText("This will clear the prompt, folder paths, and reset model options. This action cannot be undone.")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No); msg_box.setDefaultButton(QMessageBox.StandardButton.No); msg_box.setIcon(QMessageBox.Icon.Warning)
        if msg_box.exec() == QMessageBox.StandardButton.Yes:
            print("User confirmed reset. Resetting all settings.")
            self.input_path_edit.clear(); self.output_path_edit.clear(); self.prompt_edit.clear()
            self.output_ext_edit.clear(); self.delay_spinbox.setValue(10); self.thinking_mode_checkbox.setChecked(False); self.subfolders_checkbox.setChecked(False)
            self.set_default_model()

    def set_default_model(self):
        default_index = -1
        for i in range(self.model_combo.count()):
            model_name = self.model_combo.itemData(i)
            # --- FIX: Look for 2.5 flash as default ---
            if "gemini-2.5-flash" in model_name: default_index = i; break
        if default_index != -1: self.model_combo.setCurrentIndex(default_index)

    def browse_for_input_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Input Folder");
        if folder_path: self.input_path_edit.setText(folder_path)

    def browse_for_output_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Output Folder");
        if folder_path: self.output_path_edit.setText(folder_path)

    def load_api_key_and_configure(self, api_key: str, models_list: list[str]):
        print(f"Main window received API key and {len(models_list)} models.")
        self.api_key = api_key
        self.populate_models_combo(models_list)