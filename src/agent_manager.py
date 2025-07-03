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
    def __init__(self, model_name="gemini-1.5-pro", debug: bool = False, sandbox: bool = False, temperature: float = 0.7, top_p: float = 1.0, top_k: int = 40, max_output_tokens: int = 1024, grounding: bool = False, code_execution: bool = False):
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            print("python-dotenv not found. Please install it with 'pip install python-dotenv'")
        self.model_name = model_name
        self.debug = debug
        self.sandbox = sandbox
        self.temperature = temperature
        self.top_p = top_p
        self.top_k = top_k
        self.max_output_tokens = max_output_tokens
        self.grounding = grounding
        self.code_execution = code_execution
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")

    @property
    def api_url(self):
        return f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"

    def list_models(self):
        """Lists the available models."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key}"
        try:
            response = requests.get(url, timeout=120)
            response.raise_for_status()
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            return [f"Error listing models: {e}"]

    def get_direct_response(self, user_input: str, conversation_history: list) -> str:
        """Gets a direct response from the model without using tools."""
        prompt = ""
        for entry in conversation_history:
            prompt += f"{entry['role']}: {entry['content']}\n"
        prompt += f"user: {user_input}"

        generation_config = {
            "temperature": self.temperature,
            "topP": self.top_p,
            "topK": self.top_k,
            "maxOutputTokens": self.max_output_tokens,
        }

        tools = []
        if self.grounding:
            tools.append({"google_search": {}})
        if self.code_execution:
            tools.append({"code_interpreter": {}})

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": generation_config,
            "tools": tools
        }

        try:
            response = requests.post(self.api_url, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()
            response_content = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
            return {"thought": "Direct response", "response": response_content}
        except Exception as e:
            return {"thought": "Error", "response": f"API Error: {e}"}

    def start_task(self, task: Dict[str, Any], notification_queue: Optional[Queue] = None):
        task_id = task["id"]
        workspace_setup_message = workspace_manager.setup_workspace(task_id)
        task_manager.log_to_task(task_id, workspace_setup_message)

        task_manager.update_task_status(task_id, "in_progress")
        
        def notify(message: str):
            if notification_queue:
                notification_queue.put(f"[Task {task_id}] {message}")
            else:
                print(f"[Task {task_id}] {message}")

        max_steps = task.get("max_steps", 25) # Increased max steps
        try:
            current_step_count = len([h for h in task.get('history', []) if 'AI Response:' in h])
            while current_step_count < max_steps:
                
                current_task_state = task_manager.get_task(task_id)
                if current_task_state["status"] != "in_progress":
                    notify(f"Task status changed to '{current_task_state['status']}'. Stopping agent loop.")
                    break

                history_str = "\n".join(current_task_state["history"])
                prompt_text = self._get_system_prompt(
                    current_task_state["goal"], history_str, current_task_state["allowed_tools"]
                )
                
                generation_config = {
                    "temperature": self.temperature,
                    "topP": self.top_p,
                    "topK": self.top_k,
                    "maxOutputTokens": self.max_output_tokens,
                }

                tools = []
                if self.grounding:
                    tools.append({"google_search": {}})
                if self.code_execution:
                    tools.append({"code_interpreter": {}})

                payload = {
                    "contents": [{"parts": [{"text": prompt_text}]}],
                    "generationConfig": generation_config,
                    "tools": tools
                }

                try:
                    response = requests.post(self.api_url, json=payload, timeout=120)
                    response.raise_for_status()
                    data = response.json()
                    response_content = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                except Exception as e:
                    notify(f"API Error: {e}")
                    task_manager.log_to_task(task_id, f"Observation: API Error: {e}")
                    continue

                if self.debug:
                    notify(f"--- DEBUG: RAW AI RESPONSE ---\n{repr(response_content)}\n---")

                task_manager.log_to_task(task_id, f"AI Response: {response_content}")
                current_step_count += 1
                
                tool_result = ""
                try:
                    json_str = _extract_json_from_response(response_content)
                    if not json_str:
                        raise ValueError("Could not find a JSON object in the AI's response.")
                    
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
                        
                        if tool_name == 'task_complete' and 'last_tool_output' in sig.parameters:
                            last_observation = next((item for item in reversed(task_manager.get_task(task_id)['history']) if item.startswith("Observation:")), None)
                            if last_observation:
                                tool_args['last_tool_output'] = last_observation.replace("Observation: ", "")

                        # This is the crucial change: wrap tool execution in a try-except block
                        try:
                            tool_result = tool_func(**tool_args)
                            notify(f"Tool '{tool_name}' executed successfully.")
                        except Exception as e:
                            tool_result = f"Error executing tool '{tool_name}': {e}. You must analyze this error and correct your plan."
                            notify(f"[bold red]Tool Error: {tool_result}[/bold red]")

                        # Handle status changes for specific tools
                        if tool_name == 'task_complete':
                            task_manager.update_task_status(task_id, "completed_by_agent")
                        elif tool_name == 'request_user_input':
                            task_manager.update_task_status(task_id, 'pending_input')
                    
                    else:
                        tool_result = "Error: Invalid or disallowed tool call specified. You must select a tool from the available list."
                        notify(f"[bold red]{tool_result}[/bold red]")

                except (json.JSONDecodeError, ValueError, KeyError) as e:
                    tool_result = f"Error processing AI response: {e}. The response was not valid JSON with 'thought' and 'tool_call'. You must correct your response format."
                    notify(f"Agent is self-correcting due to a response formatting error...")
                
                # Log the observation for the next loop
                task_manager.log_to_task(task_id, f"Observation: {tool_result}")

                # Break the loop if the task is no longer in progress
                if task_manager.get_task(task_id)["status"] != "in_progress":
                    break
                
                max_steps = task_manager.get_task(task_id).get("max_steps", 25)

            if task_manager.get_task(task_id)["status"] == "in_progress":
                task_manager.update_task_status(task_id, "completed_max_steps")
        except Exception as e:
            import traceback
            error_msg = f"A critical error occurred in the agent loop: {e}\n{traceback.format_exc()}"
            notify(f"[bold red]{error_msg}[/bold red]")
            task_manager.log_to_task(task_id, f"Critical Error: {error_msg}")
            task_manager.update_task_status(task_id, "failed")
        
        finally:
            final_status = task_manager.get_task(task_id)['status']
            notify(f"✅ Task {task_id} finished with status: {final_status}.")