import uuid
import json
import requests
import os
import re
from typing import Dict, Any, Optional
from src import workspace_manager, tool_manager

def _extract_json_from_response(text: str) -> Optional[str]:
    """
    Robustly extracts a JSON string from the AI's response.
    Handles markdown fences, surrounding text, and leading/trailing whitespace.
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
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.task_counter = 0
        self.tool_descriptions = tool_manager.get_tool_descriptions()
        self.system_prompt_template = self._load_system_prompt()
        self.debug = debug
        
        self.model_name = model_name
        self.api_key = os.getenv('GOOGLE_API_KEY_AI_ASSISTANT')
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY_AI_ASSISTANT environment variable not set.")
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"

    def _load_system_prompt(self) -> str:
        """
        Builds the system prompt, correctly escaping literal braces for .format().
        """
        thought_process = """
**Your Thought Process:**
1.  **Analyze the Goal:** Understand what needs to be done.
2.  **Choose a Tool:** Select the best tool for the next logical step.
3.  **Provide Arguments:** Format the arguments for the chosen tool as a JSON object.
4.  **Respond:** Your response MUST be a single JSON object with two keys: "thought" and "tool_call".
    - "thought": A brief explanation of your reasoning for this step.
    - "tool_call": A dictionary with "name" and "args" for the tool you want to use. The "args" MUST include the "task_id".
"""
        # THE FIX: All literal braces in this example are doubled (e.g., {{, }})
        # to escape them for the .format() method.
        example_json = """
**Example Response Format:**
```json
{{
    "thought": "I need to create a Python file to start working on the problem.",
    "tool_call": {{
        "name": "write_file",
        "args": {{
            "task_id": "CURRENT_TASK_ID",
            "file_path": "main.py",
            "content": "print('Hello, World!')"
        }}
    }}
}}
```"""
        prompt_parts = [
            "You are an autonomous AI agent responsible for completing a given task.",
            "You will be given a high-level goal. Your job is to break it down into steps and use the available tools to accomplish it.",
            # Placeholders for .format() use SINGLE braces.
            "**Your Goal:**\n{goal}",
            "**Available Tools:**", self.tool_descriptions,
            thought_process.strip(),
            example_json.strip(),
            # Placeholders for .format() use SINGLE braces.
            "**Conversation History (Previous Steps):**\n{history}",
            "\nNow, begin. What is your first step?"
        ]
        return "\n\n".join(prompt_parts)

    def create_task(self, goal: str) -> str:
        task_id = str(self.task_counter)
        self.task_counter += 1
        workspace_manager.create_workspace(task_id)
        self.tasks[task_id] = {"goal": goal, "history": [], "status": "pending"}
        return task_id

    def start_task(self, task_id: str, max_steps: int = 10):
        if task_id not in self.tasks:
            return f"Error: Task with ID '{task_id}' not found."

        task = self.tasks[task_id]
        task["status"] = "in_progress"
        
        try:
            for step in range(max_steps):
                print(f"\n--- Task {task_id} | Step {step+1}/{max_steps} ---")
                
                history_str = "\n".join(task["history"])
                # This .format() call will now work correctly.
                prompt_text = self.system_prompt_template.format(goal=task["goal"], history=history_str).replace("CURRENT_TASK_ID", task_id)
                
                payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
                try:
                    response = requests.post(self.api_url, json=payload, timeout=120)
                    response.raise_for_status()
                    data = response.json()
                    response_content = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                except Exception as e:
                    print(f"API Error: {e}")
                    task["history"].append(f"Step {step+1} API Error: {e}")
                    continue

                if self.debug:
                    print(f"--- DEBUG: RAW AI RESPONSE ---\n{repr(response_content)}\n--- END RAW RESPONSE ---")

                task["history"].append(f"Step {step+1} AI Response: {response_content}")
                
                json_str = _extract_json_from_response(response_content)
                
                if self.debug:
                    print(f"--- DEBUG: EXTRACTED JSON STRING ---\n{repr(json_str)}\n--- END EXTRACTED STRING ---")

                if json_str is None:
                    print("Error: Could not find a valid JSON object in the AI's response.")
                    task["history"].append("Step {step+1} Error: No JSON object found.")
                    continue

                action_json = json.loads(json_str)
                thought = action_json.get("thought", "No thought provided.")
                tool_call = action_json.get("tool_call")
                
                print(f"AI Thought: {thought}")

                if tool_call and tool_call.get("name") in tool_manager.TOOLS:
                    tool_args = tool_call.get("args", {})
                    if 'task_id' not in tool_args:
                        tool_args['task_id'] = task_id
                    result = tool_manager.TOOLS[tool_call["name"]](**tool_args)
                    print(f"Tool Result: {result}")
                    task["history"].append(f"Step {step+1} Tool Result: {result}")
                else:
                    print("Error: Invalid or missing tool call in AI response.")
                    task["history"].append("Step {step+1} Error: Invalid tool call.")

            task["status"] = "completed"
        except Exception as e:
            import traceback
            print(f"\n[bold red]A critical error occurred during task execution: {e}[/bold red]")
            traceback.print_exc()
            task["status"] = "failed"

        workspace_manager.cleanup_workspace(task_id)
        return f"Task {task_id} finished with status: {task['status']}."
