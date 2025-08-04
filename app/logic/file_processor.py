# app/logic/file_processor.py
# This file contains the core engine for scanning and processing files.

import os
import time
from PySide6.QtCore import QObject, Signal
from .api_handler import GeminiAPIHandler

class FileProcessor(QObject):
    """
    The core worker for file processing. Runs in a separate thread.
    Communicates with the main UI via signals.
    """
    processing_finished = Signal(str, list)
    progress_updated = Signal(int, int, str)

    def __init__(self, settings: dict):
        super().__init__()
        self.settings = settings
        self.files_to_process = []
        self._is_running = True
        self._is_paused = False
        self.api_handler = GeminiAPIHandler(api_key=settings.get("api_key"))

    @staticmethod
    def scan_input_folder(input_path: str, output_path: str, process_subfolders: bool = False) -> dict:
        """
        Scans the input and output folders to generate a pre-flight report.
        """
        report = {
            "files_found": 0, "subfolders_found": False, "formats": set(),
            "output_has_files": False, "warnings": []
        }
        if not os.path.isdir(input_path):
            report["warnings"].append("Input path is not a valid folder.")
            return report

        # --- UPDATED: Scan logic to handle subfolders ---
        for dirpath, dirnames, filenames in os.walk(input_path):
            if dirpath != input_path:
                report["subfolders_found"] = True

            # If not processing subfolders, we only care about the top level
            if not process_subfolders and dirpath != input_path:
                continue

            for filename in filenames:
                report["files_found"] += 1
                ext = os.path.splitext(filename)[1].lower()
                report["formats"].add(ext if ext else ".no_extension")
        # --- END UPDATED ---

        if os.path.isdir(output_path) and any(os.scandir(output_path)):
            report["output_has_files"] = True

        # --- UPDATED: Warning logic ---
        if report["subfolders_found"] and not process_subfolders:
            report["warnings"].append("• Input folder contains subfolders. They will be ignored. (Enable 'Process Subfolders' to include them).")
        # --- END UPDATED ---

        if len(report["formats"]) > 1: report["warnings"].append(f"• Multiple file formats found: {', '.join(sorted(list(report['formats'])))}.")
        if report["output_has_files"]: report["warnings"].append("• Output folder is not empty. Existing files may be overwritten.")
        if report["files_found"] == 0: report["warnings"].append("• No files found in the input folder.")
        return report

    def run(self):
        """The main processing loop that runs in a thread."""
        input_path = self.settings.get("input_path")
        output_path = self.settings.get("output_path")
        system_prompt = self.settings.get("prompt_text")
        model_name = self.settings.get("selected_model_name")
        output_extension = self.settings.get("output_extension", "").strip()
        processing_delay = self.settings.get("processing_delay", 1)
        thinking_mode = self.settings.get("thinking_mode", False)
        process_subfolders = self.settings.get("process_subfolders", False) # <-- NEW

        error_log = []
        success_count = 0

        if not all([input_path, output_path, system_prompt, model_name]):
            self.processing_finished.emit("Error: Missing required settings.", [])
            return

        self.api_handler.set_model(model_name)

        final_system_prompt = system_prompt
        if thinking_mode:
            print("Thinking Mode is ENABLED. Prepending instructions to system prompt.")
            thinking_instruction = (
                "Before you begin, first think step-by-step to thoroughly understand the user's request below. "
                "Formulate a detailed, internal plan to process the text according to all the provided rules. "
                "After you have a clear plan, execute it on the text. "
                "CRITICAL INSTRUCTION: Your final output must contain ONLY the fully processed text itself. "
                "Do NOT include your thoughts, your plan, or any other conversational phrases or markdown formatting in your response."
            )
            final_system_prompt = f"{thinking_instruction}\n\n---\n\n{system_prompt}"

        try:
            # --- UPDATED: File collection logic ---
            self.files_to_process = []
            if process_subfolders:
                for dirpath, _, filenames in os.walk(input_path):
                    for filename in filenames:
                        self.files_to_process.append(os.path.join(dirpath, filename))
            else:
                self.files_to_process = [os.path.join(input_path, f) for f in os.listdir(input_path) if os.path.isfile(os.path.join(input_path, f))]
            # --- END UPDATED ---
        except OSError as e:
            self.processing_finished.emit(f"Error reading input folder: {e}", [])
            return

        total_files = len(self.files_to_process)
        if total_files == 0:
            self.processing_finished.emit("Processing finished: No files to process.", [])
            return

        for i, file_path in enumerate(self.files_to_process):
            if not self._is_running:
                self.processing_finished.emit("Processing stopped by user.", error_log)
                return
            while self._is_paused:
                time.sleep(0.5)
                if not self._is_running:
                    self.processing_finished.emit("Processing stopped by user.", error_log)
                    return

            original_file_name = os.path.basename(file_path)
            self.progress_updated.emit(i + 1, total_files, original_file_name)

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()

                print(f"Sending to API: {original_file_name}")
                processed_content = self.api_handler.generate_content(
                    final_system_prompt,
                    file_content
                )

                if processed_content.startswith("ERROR:"):
                    error_msg = f"File: {original_file_name} | {processed_content}"
                    print(f"API Error: {error_msg}")
                    error_log.append(error_msg)
                    continue

                # --- UPDATED: Output path and filename logic ---
                relative_path = os.path.relpath(file_path, input_path)
                base_name, original_ext = os.path.splitext(relative_path)

                if output_extension:
                    if not output_extension.startswith('.'):
                        output_extension = '.' + output_extension
                    final_relative_path = base_name + output_extension
                else:
                    final_relative_path = relative_path

                output_file_path = os.path.join(output_path, final_relative_path)

                # Ensure the output directory exists
                os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
                # --- END UPDATED ---

                with open(output_file_path, 'w', encoding='utf-8') as f:
                    f.write(processed_content)

                print(f"Successfully saved: {output_file_path}")
                success_count += 1

            except Exception as e:
                error_msg = f"File: {original_file_name} | A file system or other critical error occurred: {e}"
                print(error_msg)
                error_log.append(error_msg)
                continue

            if i < total_files - 1:
                time.sleep(processing_delay)

        if self._is_running:
            summary_message = ""
            if not error_log:
                summary_message = f"Successfully processed {success_count} of {total_files} files."
            else:
                summary_message = f"Processing finished with issues. \nProcessed: {success_count} | Failed: {len(error_log)}"
            self.processing_finished.emit(summary_message, error_log)

    def stop(self):
        self._is_running = False

    def toggle_pause(self, paused: bool):
        self._is_paused = paused