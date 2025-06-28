import subprocess
import os
import base64
import re
import requests
import json
from pathlib import Path
from typing import Callable, Dict, List

from src import workspace_manager

# --- Tool Implementations ---

def write_file(task_id: str, file_path: str, content_base64: str) -> str:
    """
    Decodes a Base64 string and writes the resulting content to a file.
    :param task_id: The ID of the current task.
    :param file_path: The relative path to the file within the workspace.
    :param content_base64: The Base64 encoded string of the content to write.
    """
    try:
        full_path = workspace_manager.get_workspace_path(task_id, file_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        decoded_content = base64.b64decode(content_base64)
        with open(full_path, 'wb') as f:
            f.write(decoded_content)
        return f"Successfully wrote {len(decoded_content)} bytes to {file_path}"
    except Exception as e:
        return f"Error writing file: {e}"

def execute_python_code(task_id: str, file_path: str) -> str:
    """Executes a Python script from the task's workspace."""
    try:
        full_path = workspace_manager.get_workspace_path(task_id, file_path)
        if not full_path.exists():
            return f"Error: Cannot execute file, '{file_path}' does not exist."
        result = subprocess.run(["python", str(full_path)], capture_output=True, text=True, timeout=30)
        return f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    except Exception as e:
        return f"Error executing Python code: {e}"

def run_pytest(task_id: str) -> str:
    """Runs pytest within the task's workspace."""
    try:
        workspace_path = workspace_manager.BASE_WORKSPACE_DIR / task_id
        result = subprocess.run(["pytest", str(workspace_path)], capture_output=True, text=True, timeout=60)
        return f"PYTEST RESULTS:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    except Exception as e:
        return f"Error running pytest: {e}"

def web_search(query: str, num_results: int = 5) -> str:
    """
    Performs a web search using DuckDuckGo's HTML interface and returns the results.
    This tool has no special dependencies and does not require an API key.
    :param query: The search query.
    :param num_results: The maximum number of results to return.
    """
    url = "https://html.duckduckgo.com/html/"
    params = {"q": query}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.post(url, data=params, headers=headers, timeout=10)
        response.raise_for_status()

        # Simple regex to parse the HTML results
        results = re.findall(r'a class="result__a" href="([^"]+)">(.*?)</a>.*?<a class="result__snippet".*?>(.*?)</a>', response.text, re.DOTALL)
        
        if not results:
            return "No results found."

        output = []
        for i, (link, title, snippet) in enumerate(results):
            if i >= num_results:
                break
            output.append({
                "title": re.sub('<.*?>', '', title), # Strip HTML tags from title
                "href": link,
                "body": re.sub('<.*?>', '', snippet) # Strip HTML tags from snippet
            })
        
        return json.dumps(output, indent=2)

    except Exception as e:
        return f"Error performing web search: {e}"

def task_complete(task_id: str, reason: str) -> str:
    """
    Call this tool ONLY when the user's request has been fully satisfied.
    :param task_id: The ID of the current task.
    :param reason: A brief summary of why the task is considered complete.
    """
    return f"Task marked as complete by the agent. Reason: {reason}"

TOOLS: Dict[str, Callable] = {
    "write_file": write_file,
    "execute_python_code": execute_python_code,
    "run_pytest": run_pytest,
    "web_search": web_search,
    "task_complete": task_complete,
}

def get_tool_descriptions(allowed_tools: List[str]) -> str:
    """Generates a formatted string of descriptions for the allowed tools."""
    descriptions = []
    for name in allowed_tools:
        if name in TOOLS:
            func = TOOLS[name]
            doc_lines = [line.strip() for line in func.__doc__.strip().split('\n')]
            formatted_doc = "\n  ".join(doc_lines)
            descriptions.append(f"- {name}:\n  {formatted_doc}")
    return "\n".join(descriptions)
