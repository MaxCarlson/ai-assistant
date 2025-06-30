import uuid
import json
import requests
import os
import re
import inspect
from typing import Dict, Any, Optional, List
from queue import Queue
from src import workspace_manager, tool_manager, task_manager

def _extract_json_from_response(text: str) -> Optional[str]:
    """
    Robustly extracts a JSON string from the AI's response.
    This is now a module-level function for easier testing.
    """
    fence_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()

    start_index = text.find('{')
    end_index = text.rfind('}')
    if start_index != -1 and end_index != -1 and end_index > start_index:
        return text[start_index:end_index+1].strip()
        
    return None

class AgentManager:
    def __init__(self, model_name="gemini-1.5-pro", debug: bool = False):
        self.model_name = model_name
        self.debug = debug
        self.api_key = os.getenv('GOOGLE_API_KEY_AI_ASSISTANT')
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY_AI_ASSISTANT environment variable not set.")
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"

    def _get_system_prompt(self, goal: str, history: str, allowed_tools: List[str]) -> str:
        """Builds the system prompt dynamically based on the allowed tools."""
        tool_descriptions = tool_manager.get_tool_descriptions(allowed_tools)
        
        prompt_parts = [
            "You are an expert-level autonomous software engineer agent. Your goal is to solve the user's request by writing and modifying code.",
            "**Your Goal:**", goal,
            "**Your Thought Process & Self-Correction:**",
            "1.  Analyze the user's goal and the available tools.",
            "2.  If the goal is ambiguous, you MUST use `request_user_input` immediately.",
            "3.  **CRITICAL:** If a tool returns an error, first use `read_file` to inspect the code. Then, for small corrections (like fixing a typo or one line of code), you MUST use the `modify_file` tool. Only use `write_file` to create a new file or if the file requires a complete rewrite.",
            "4.  **Pytest Note:** If you get a `ModuleNotFoundError` when running `run_pytest`, do not try to create `__init__.py` files. The tool handles the `PYTHONPATH` automatically. The error means your `import` statement is wrong in the test file. Use `read_file` and `modify_file` to fix the import.",
            "5.  When the goal is fully achieved, use the `task_complete` tool.",
            "**Response Format:**",
            "You MUST respond with a single JSON object enclosed in ```json ... ```. The `content` argument for `write_file` must be a valid JSON string. This means all newline characters within the code MUST be escaped as `\\n`.",
            f"""**Example for `write_file`:**
```json
{{
    "thought": "I will create a simple python script.",
    "tool_call": {{
        "name": "write_file",
        "args": {{
            "task_id": "CURRENT_TASK_ID",
            "file_path": "hello.py",
            "content": "def main():\\n    print('Hello, World!')\\n\\nif __name__ == '__main__':\\n    main()"
        }}
    }}
}}
```""",
            f"**Conversation History (Previous Steps):**\n{history}",
            "\nNow, begin. What is your next step?"
        ]
        return "\n\n".join(prompt_parts)

    def start_task(self, task_id: str, notification_queue: Optional[Queue] = None):
        workspace_manager.create_workspace(task_id)
        
        task = task_manager.get_task(task_id)
        if not task:
            if notification_queue:
                notification_queue.put(f"[Agent Error] Task with ID '{task_id}' not found.")
            else:
                print(f"[Agent Error] Task with ID '{task_id}' not found.")
            return

        task_manager.update_task_status(task_id, "in_progress")
        
        def notify(message: str):
            if notification_queue:
                notification_queue.put(f"[Task {task_id}] {message}")
            else:
                print(f"[Task {task_id}] {message}")

        max_steps = task.get("max_steps", 15)
        try:
            current_step_count = len([h for h in task.get('history', []) if h.startswith('AI Response:')])
            while current_step_count < max_steps:
                
                current_task_state = task_manager.get_task(task_id)
                history_str = "\n".join(current_task_state["history"])
                prompt_text = self._get_system_prompt(
                    current_task_state["goal"], history_str, current_task_state["allowed_tools"]
                ).replace("CURRENT_TASK_ID", task_id)
                
                payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
                try:
                    response = requests.post(self.api_url, json=payload, timeout=120)
                    response.raise_for_status()
                    data = response.json()
                    response_content = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                except Exception as e:
                    notify(f"API Error: {e}")
                    task_manager.log_to_task(task_id, f"API Error: {e}")
                    continue

                if self.debug:
                    notify(f"--- DEBUG: RAW AI RESPONSE ---\n{repr(response_content)}\n---")

                task_manager.log_to_task(task_id, f"AI Response: {response_content}")
                current_step_count += 1
                
                try:
                    json_str = _extract_json_from_response(response_content)
                    if not json_str:
                        raise json.JSONDecodeError("Could not find a JSON object in the AI's response.", response_content, 0)
                    
                    action_json = json.loads(json_str)
                    thought = action_json.get("thought", "No thought provided.")
                    tool_call = action_json.get("tool_call")
                    
                    notify(f"AI Thought: {thought}")

                    if tool_call and tool_call.get("name") in current_task_state["allowed_tools"]:
                        tool_name = tool_call["name"]
                        tool_func = tool_manager.TOOLS[tool_name]
                        tool_args = tool_call.get("args", {})
                        
                        sig = inspect.signature(tool_func)
                        if 'task_id' in sig.parameters:
                            tool_args['task_id'] = task_id
                        
                        if tool_name == 'request_user_input':
                            task_manager.update_task_status(task_id, 'pending_input')
                        
                        result = tool_func(**tool_args)
                        notify(f"Tool Result: {result}")
                        task_manager.log_to_task(task_id, f"Tool Result: {result}")

                        if tool_name == 'task_complete':
                            task_manager.update_task_status(task_id, "completed_by_agent")
                            break
                        if tool_name == 'request_user_input':
                            notify("Task paused, waiting for user input.")
                            break
                    else:
                        error_msg = "Error: Invalid or disallowed tool call. The agent might be stuck in a loop if it cannot select a tool."
                        notify(error_msg)
                        task_manager.log_to_task(task_id, error_msg)

                except Exception as e:
                    error_msg = f"Error processing step: {e}"
                    notify(error_msg)
                    task_manager.log_to_task(task_id, error_msg)
                    continue
                
                max_steps = task_manager.get_task(task_id).get("max_steps", 15)

            if task_manager.get_task(task_id)["status"] == "in_progress":
                task_manager.update_task_status(task_id, "completed_max_steps")

        except Exception as e:
            import traceback
            error_msg = f"A critical error occurred: {e}\n{traceback.format_exc()}"
            notify(f"[bold red]{error_msg}[/bold red]")
            task_manager.log_to_task(task_id, error_msg)
            task_manager.update_task_status(task_id, "failed")
        
        finally:
            final_status = task_manager.get_task(task_id)['status']
            if final_status not in ['pending_input', 'completed_by_agent']:
                 notify(f"✅ Task {task_id} finished with status: {final_status}.")
