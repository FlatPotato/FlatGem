# app/logic/api_handler.py
# This file contains the logic for interacting with the Google Gemini API.

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.api_core import exceptions as google_exceptions
import re

# The incorrect circular import that caused the error has been removed from here.

DISABLED_SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

class GeminiAPIHandler:
    """
    Handles all communication with the Google Gemini API.
    """
    def __init__(self, api_key: str):
        """Initializes the handler with a specific API key."""
        # Sanitize the key to be safe.
        if api_key:
            api_key = api_key.strip()
        genai.configure(api_key=api_key)
        self.model = None

    def set_model(self, model_name: str):
        """Sets the generative model to be used for requests."""
        try:
            # We need to make sure model_name is not None or empty
            if model_name:
                self.model = genai.GenerativeModel(model_name)
                print(f"Model set to: {model_name}")
            else:
                print("Error: Model name is empty. Cannot set model.")
                self.model = None
        except Exception as e:
            print(f"Error setting model: {e}")
            self.model = None

    def generate_content(self, system_prompt: str, user_prompt: str) -> str:
        """
        Generates content using the configured model.

        Args:
            system_prompt: The instructions for the AI.
            user_prompt: The content to be processed (e.g., file content).

        Returns:
            The generated text from the AI, or an error message.
        """
        if not self.model:
            return "ERROR: Model is not set or failed to initialize."

        try:
            # Re-creating the model with the system prompt for this generation
            # This is how system prompts are handled correctly in the genai library
            model_with_system_prompt = genai.GenerativeModel(
                self.model.model_name,
                system_instruction=system_prompt
            )

            # --- FIX START ---
            # Removed all logic related to 'tools' and 'use_grounding' as the
            # feature is not supported and caused errors.
            response = model_with_system_prompt.generate_content(
                user_prompt,
                safety_settings=DISABLED_SAFETY_SETTINGS
            )
            # --- FIX END ---
            return response.text
        except Exception as e:
            error_message = f"ERROR: An exception occurred during generation: {e}"
            print(error_message)
            return error_message

    @staticmethod
    def is_api_key_valid(api_key: str) -> tuple[bool, str]:
        """
        Validates an API key.

        Returns:
            A tuple containing a boolean (True if valid, False otherwise)
            and a status message string for the user.
        """
        if api_key:
            api_key = api_key.strip()

        if not api_key:
            return (False, "Please enter an API key.")
        try:
            # This configure is temporary and only for this check
            genai.configure(api_key=api_key)
            # A simple, low-cost operation to test the key.
            # Using a lightweight model like flash is sufficient.
            model = genai.GenerativeModel('gemini-2.5-flash')
            model.count_tokens("test")
            return (True, "✅ API Key is valid!")
        except (google_exceptions.PermissionDenied, google_exceptions.Unauthenticated, google_exceptions.GoogleAPICallError):
            # Grouping all invalid key errors together.
            return (False, "❌ Invalid API Key. Please check the key and try again.")
        except Exception:
            # Any other error is treated as a connection issue.
            return (False, "🌐 Could not connect. Please check your internet connection.")


    @staticmethod
    def get_available_models() -> list[str]:
        """
        Fetches and sorts the list of available models from the Gemini API.
        """
        try:
            # This method is only called AFTER a key is known to be valid.
            model_list = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            print(f"Successfully fetched {len(model_list)} available models.")
            gemini_models = sorted([m for m in model_list if 'gemini' in m], reverse=True)
            gemma_models = sorted([m for m in model_list if 'gemma' in m and 'gemini' not in m], reverse=True)
            other_models = sorted([m for m in model_list if 'gemini' not in m and 'gemma' not in m], reverse=True)
            return gemini_models + gemma_models + other_models
        except Exception as e:
            print(f"Could not fetch model list: {e}")
            return ['gemini-1.5-pro-latest', 'gemini-2.5-flash']