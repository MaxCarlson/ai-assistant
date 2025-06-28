import os
import requests
from src.base_agent import BaseAgent

class MinimalAgent(BaseAgent):
    """
    A minimal agent that interacts directly with the Gemini REST API using 'requests'.
    It is stateless and sends the entire conversation history with each call.
    Designed for maximum portability in environments like Termux.
    """
    def __init__(self, model_name="gemini-2.5-pro"):
        self.model_name = model_name
        self.api_key = os.getenv('GOOGLE_API_KEY_AI_ASSISTANT')
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY_AI_ASSISTANT environment variable not set.")
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"

    def _format_history_for_api(self, conversation_history: list) -> list:
        """
        Transforms the internal history format to the Gemini REST API format.
        Maps the 'assistant' role to 'model'.
        """
        api_history = []
        for entry in conversation_history:
            # The API expects 'user' and 'model' roles.
            role = "model" if entry["role"] == "assistant" else "user"
            api_history.append({"role": role, "parts": [{"text": entry["content"]}]})
        return api_history

    def handle_task(self, user_input: str, conversation_history: list) -> str:
        """
        Sends the user input and conversation history to the Gemini REST API
        and returns the response.
        """
        contents = self._format_history_for_api(conversation_history)
        contents.append({"role": "user", "parts": [{"text": user_input}]})

        payload = {"contents": contents}

        try:
            response = requests.post(self.api_url, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()

            if 'candidates' in data and data['candidates']:
                candidate = data['candidates'][0]
                if candidate.get('finishReason') == 'SAFETY':
                    return "[Error] The response was blocked due to safety settings."
                
                content = candidate.get('content', {})
                parts = content.get('parts', [])
                if parts:
                    return parts[0].get('text', "[Error] No text found in response part.")

            return f"[Error] Could not parse a valid response from API. Response: {data}"

        except requests.exceptions.RequestException as e:
            return f"[Network Error] Failed to connect to Gemini API: {e}"
        except Exception as e:
            return f"[Error] An unexpected error occurred: {e}"
