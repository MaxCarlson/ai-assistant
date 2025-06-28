import uuid
import json
import requests
import os
import re
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
            "You are an autonomous AI agent. Your primary goal is to solve the user's request by using a set of tools.",
            "**Your Goal:**", goal,
            "**Your Thought Process:**",
            "1.  Analyze the user's goal.",
            "2.  If the goal is ambiguous or you need more information, you MUST use the `request_user_input` tool immediately. Do not attempt to proceed without clarification.",
            "3.  If the goal is clear, formulate a plan and select the best tool to execute the first step.",
            "4.  Observe the result of the tool execution.",
            "5.  Based on the result, decide on the next step, which could be using another tool, or marking the task as complete with `task_complete`.",
            "**Available Tools:**", tool_descriptions,
            "**Response Format:**",
            "You MUST respond with a single JSON object enclosed in ```json ... ```.",
            "The JSON object must contain your 'thought' and the 'tool_call' you want to make. If you are only thinking or waiting, `tool_call` can be `null`.",
            f"""**Example Response Format:**
```json
{{
    "thought": "I need to ask the user for the filename.",
    "tool_call": {{
        "name": "request_user_input",
        "args": {{
            "task_id": "CURRENT_TASK_ID",
            "question": "What should I name the output file?"
        }}
    }}
}}
```""",
            f"**Conversation History (Previous Steps):**\n{history}",
            "\nNow, begin. What is your next step?"
        ]
        return "\n\n".join(prompt_parts)

    def start_task(self, task_id: str, notification_queue: Optional[Queue] = None):
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
            for step in range(max_steps):
                notify(f"--- Step {step+1}/{max_steps} ---")
                
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
                        tool_args = tool_call.get("args", {})
                        if 'task_id' not in tool_args:
                            tool_args['task_id'] = task_id
                        
                        # The agent manager handles state changes based on the tool call
                        if tool_name == 'request_user_input':
                            task_manager.update_task_status(task_id, 'pending_input')
                        
                        result = tool_manager.TOOLS[tool_name](**tool_args)
                        notify(f"Tool Result: {result}")
                        task_manager.log_to_task(task_id, f"Tool Result: {result}")

                        # The agent manager stops the loop based on the tool call
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

            if task_manager.get_task(task_id)["status"] == "in_progress":
                task_manager.update_task_status(task_id, "completed_max_steps")

        except Exception as e:
            import traceback
            error_msg = f"A critical error occurred: {e}\n{traceback.format_exc()}"
            notify(f"[bold red]{error_msg}[/bold red]")
            task_manager.log_to_task(task_id, error_msg)
            task_manager.update_task_status(task_id, "failed")
        
        finally:
            workspace_manager.cleanup_workspace(task_id)
            final_status = task_manager.get_task(task_id)['status']
            notify(f"✅ Task {task_id} finished with status: {final_status}. Workspace cleaned up.")
