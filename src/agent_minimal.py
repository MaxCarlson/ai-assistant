import subprocess
import json
from src.base_agent import BaseAgent

class MinimalAgent(BaseAgent):
    """
    A minimal agent that interacts with the Gemini CLI.
    It is stateless and sends the entire conversation history with each call.
    Designed for maximum portability in environments like Termux.
    """
    def __init__(self, model_name="gemini-2.5-pro"):
        self.model_name = model_name

    def handle_task(self, user_input: str, conversation_history: list) -> dict:
        """
        Sends the user input and conversation history to the Gemini CLI
        and returns the response as a dictionary with 'thought' and 'response'.
        """
        prompt = "You are a helpful assistant. Please provide a thoughtful response."
        prompt += "\n\n---\n\n"
        for entry in conversation_history:
            prompt += f"{entry['role']}: {entry['content']['response'] if isinstance(entry['content'], dict) else entry['content']}\n"
        prompt += f"user: {user_input}"

        command = [
            "gemini",
            "-m",
            self.model_name,
            "-p",
            prompt,
        ]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                timeout=120
            )
            response_text = result.stdout.strip()
            # For the minimal agent, we'll just put the response in both fields
            return {"thought": "Thinking...", "response": response_text}
        except FileNotFoundError:
            return {"thought": "Error", "response": "[Error] 'gemini' command not found. Make sure the Gemini CLI is installed and in your PATH."}
        except subprocess.CalledProcessError as e:
            return {"thought": "Error", "response": f"[Error] The gemini CLI returned a non-zero exit code {e.returncode}.\nStderr: {e.stderr}"}
        except subprocess.TimeoutExpired:
            return {"thought": "Error", "response": "[Error] The gemini CLI command timed out."}
        except Exception as e:
            return {"thought": "Error", "response": f"[Error] An unexpected error occurred: {e}"}
