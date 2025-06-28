import uuid
import json
import requests
import os
import re
from typing import Dict, Any, Optional
from queue import Queue
from src import workspace_manager, tool_manager

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
        Builds the system prompt template. Note the placeholders for goal, history, and the example.
        """
        thought_process = """
**Your Thought Process:**
1.  **Analyze the Goal:** Understand what needs to be done.
2.  **Choose a Tool:** Select the best tool for the next logical step.
3.  **Provide Arguments:** Format the arguments for the chosen tool as a JSON object.
4.  **IMPORTANT FOR `write_file`:** The `content_base64` argument MUST be a Base64 encoded string.
5.  **Signal Completion:** When the request is fully satisfied, you MUST call the `task_complete` tool.
6.  **Respond:** Your response MUST be a single JSON object with "thought" and "tool_call".
"""
        prompt_parts = [
            "You are an autonomous AI agent responsible for completing a given task.",
            "You will be given a high-level goal. Your job is to break it down into steps and use the available tools to accomplish it.",
            "**Your Goal:**\n{goal}",
            "**Available Tools:**", self.tool_descriptions,
            thought_process.strip(),
            # A placeholder for the example, which will be formatted separately.
            "{example_json}",
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

    def start_task(self, task_id: str, notification_queue: Queue, max_steps: int = 15):
        if task_id not in self.tasks:
            notification_queue.put(f"[Agent Error] Task with ID '{task_id}' not found.")
            return

        task = self.tasks[task_id]
        task["status"] = "in_progress"
        
        def notify(message: str):
            notification_queue.put(f"[Task {task_id}] {message}")

        try:
            for step in range(max_steps):
                notify(f"--- Step {step+1}/{max_steps} ---")
                
                history_str = "\n".join(task["history"])

                # THE DEFINITIVE FIX: Assemble the prompt here, preventing format conflicts.
                hello_world_base64 = "cHJpbnQoJ0hlbGxvLCBXb3JsZCEnKQ=="
                example_json_formatted = f"""
**Example Response Format:**
```json
{{
    "thought": "I need to create a Python file. I will encode its content in Base64.",
    "tool_call": {{
        "name": "write_file",
        "args": {{
            "task_id": "{task_id}",
            "file_path": "main.py",
            "content_base64": "{hello_world_base64}"
        }}
    }}
}}
```"""
                prompt_text = self.system_prompt_template.format(
                    goal=task["goal"], 
                    history=history_str,
                    example_json=example_json_formatted
                )
                
                payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
                try:
                    response = requests.post(self.api_url, json=payload, timeout=120)
                    response.raise_for_status()
                    data = response.json()
                    response_content = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                except Exception as e:
                    notify(f"API Error: {e}")
                    task["history"].append(f"Step {step+1} API Error: {e}")
                    continue

                if self.debug:
                    notify(f"--- DEBUG: RAW AI RESPONSE ---\n{repr(response_content)}\n---")

                task["history"].append(f"Step {step+1} AI Response: {response_content}")
                
                try:
                    json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_content, re.DOTALL)
                    if not json_match:
                        raise json.JSONDecodeError("No JSON block found in markdown fence.", response_content, 0)
                    
                    json_str = json_match.group(1).strip()
                    action_json = json.loads(json_str)
                    thought = action_json.get("thought", "No thought provided.")
                    tool_call = action_json.get("tool_call")
                    
                    notify(f"AI Thought: {thought}")

                    if tool_call and tool_call.get("name") in tool_manager.TOOLS:
                        tool_name = tool_call["name"]
                        tool_args = tool_call.get("args", {})
                        if 'task_id' not in tool_args:
                            tool_args['task_id'] = task_id
                            
                        result = tool_manager.TOOLS[tool_name](**tool_args)
                        notify(f"Tool Result: {result}")
                        task["history"].append(f"Step {step+1} Tool Result: {result}")

                        if tool_name == 'task_complete':
                            notify("Task marked as complete by agent.")
                            task["status"] = "completed_by_agent"
                            break
                    else:
                        error_msg = "Error: Invalid or missing tool call in AI response."
                        notify(error_msg)
                        task["history"].append(f"Step {step+1} {error_msg}")

                except Exception as e:
                    error_msg = f"Error processing step: {e}"
                    notify(error_msg)
                    task["history"].append(f"Step {step+1} {error_msg}")
                    continue

            if task["status"] == "in_progress":
                task["status"] = "completed_max_steps"

        except Exception as e:
            import traceback
            notify(f"[bold red]A critical error occurred: {e}[/bold red]")
            print("\n--- TRACEBACK ---")
            traceback.print_exc()
            print("--- END TRACEBACK ---")
            task["status"] = "failed"
        
        finally:
            workspace_manager.cleanup_workspace(task_id)
            notification_queue.put(f"✅ Task {task_id} finished with status: {task['status']}. Workspace cleaned up.")
