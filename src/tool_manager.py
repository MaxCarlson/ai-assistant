import subprocess
import os
import base64
import re
import requests
import json
from pathlib import Path
from typing import Callable, Dict, List, Any, Optional

from src import workspace_manager

# --- Tool Implementations ---

def write_file(task_id: str, file_path: str, content: str) -> str:
    """
    Writes the given string content to a file in the workspace.
    This overwrites the entire file. For small changes, consider using 'modify_file'.
    :param task_id: The ID of the current task.
    :param file_path: The relative path to the file within the workspace.
    :param content: The plain text content to write to the file.
    """
    if task_id is None:
        return "Error: task_id is a required argument for write_file."
    try:
        full_path = workspace_manager.get_safe_path(task_id, file_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        # Write in text mode, which is simpler and correct for code.
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote {len(content)} characters to {file_path}"
    except Exception as e:
        return f"Error writing file: {e}"

def read_file(task_id: str, file_path: str) -> str:
    """
    Reads the content of a file from the workspace and returns it as a string.
    :param task_id: The ID of the current task.
    :param file_path: The relative path to the file within the workspace.
    """
    if task_id is None:
        return "Error: task_id is a required argument for read_file."
    try:
        full_path = workspace_manager.get_safe_path(task_id, file_path)
        if not full_path.exists():
            return f"Error: File '{file_path}' not found."
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

def modify_file(task_id: str, file_path: str, changes: List[Dict[str, Any]]) -> str:
    """
    Modifies a file in the workspace based on a list of changes.
    Use this for targeted edits instead of overwriting the whole file.
    :param task_id: The ID of the current task.
    :param file_path: The relative path to the file to modify.
    :param changes: A list of change operations. Each change is a dictionary.
                    Example: [{"action": "replace", "line_number": 5, "new_content": "corrected code"},
                              {"action": "delete", "line_number": 10},
                              {"action": "append", "content": "new line at the end"}]
    """
    if task_id is None:
        return "Error: task_id is a required argument for modify_file."
    try:
        full_path = workspace_manager.get_safe_path(task_id, file_path)
        if not full_path.exists():
            return f"Error: File '{file_path}' not found."
        
        with open(full_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Note: line numbers are 1-based for the agent, but list indices are 0-based.
        for change in changes:
            action = change.get("action")
            if action == "replace":
                line_num = change.get("line_number", 0) - 1
                if 0 <= line_num < len(lines):
                    lines[line_num] = change.get("new_content", "") + "\n"
            elif action == "delete":
                line_num = change.get("line_number", 0) - 1
                if 0 <= line_num < len(lines):
                    lines.pop(line_num)
            elif action == "append":
                lines.append(change.get("content", "") + "\n")
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        return f"Successfully modified {file_path}."
    except Exception as e:
        return f"Error modifying file: {e}"


def execute_python_code(task_id: str, file_path: str) -> str:
    """
    Executes a Python script from the task's workspace.
    IMPORTANT: This tool ONLY accepts a 'file_path'. It does NOT accept raw code.
    :param task_id: The ID of the current task.
    :param file_path: The relative path to the Python script to execute.
    """
    if task_id is None:
        return "Error: task_id is a required argument for execute_python_code."
    try:
        full_path = workspace_manager.get_safe_path(task_id, file_path)
        if not full_path.exists():
            return f"Error: Cannot execute file, '{file_path}' does not exist."
        
        workspace_dir = workspace_manager.get_task_workspace(task_id)
        result = subprocess.run(
            ["python", str(full_path)], 
            capture_output=True, text=True, timeout=30, cwd=workspace_dir
        )
        return f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    except Exception as e:
        return f"Error executing Python code: {e}"

def run_pytest(task_id: str, args: Optional[List[str]] = None) -> str:
    """
    Runs pytest within the task's workspace. Automatically handles PYTHONPATH.
    If '--cov' is in the arguments, it will attempt to install 'pytest-cov' if not found.
    :param task_id: The ID of the current task.
    :param args: Optional list of arguments to pass to pytest (e.g., ['-vv', '--cov']).
    """
    if task_id is None:
        return "Error: task_id is a required argument for run_pytest."
    try:
        workspace_path = workspace_manager.get_task_workspace(task_id)
        
        env = os.environ.copy()
        env['PYTHONPATH'] = f"{workspace_path}:{env.get('PYTHONPATH', '')}"
        
        command = ["pytest"] + (args or [])

        # Check for coverage flag and try to install if needed
        if any(arg.startswith('--cov') for arg in (args or [])):
            try:
                import pytest_cov
            except ImportError:
                install_command = [sys.executable, "-m", "pip", "install", "pytest-cov"]
                install_result = subprocess.run(install_command, capture_output=True, text=True)
                if install_result.returncode != 0:
                    return f"Failed to auto-install pytest-cov: {install_result.stderr}"

        result = subprocess.run(
            command, 
            capture_output=True, 
            text=True, 
            timeout=60, 
            cwd=workspace_path,
            env=env
        )
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
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.post(url, data=params, headers=headers, timeout=10)
        response.raise_for_status()
        results = re.findall(r'a class="result__a" href="([^"]+)">(.*?)</a>.*?<a class="result__snippet".*?>(.*?)</a>', response.text, re.DOTALL)
        if not results: return "No results found."
        output = [{"title": re.sub('<.*?>', '', t), "href": h, "body": re.sub('<.*?>', '', s)} for h, t, s in results[:num_results]]
        return json.dumps(output, indent=2)
    except Exception as e:
        return f"Error performing web search: {e}"

def request_user_input(task_id: str, question: str) -> str:
    """
    Pauses the task and asks the user for input. The user will respond with a separate command.
    :param task_id: The ID of the current task.
    :param question: The question to ask the user.
    """
    return f"Task paused. User was asked: {question}"

def task_complete(task_id: str, reason: str) -> str:
    """
    Call this tool ONLY when the user's request has been fully satisfied.
    :param task_id: The ID of the current task.
    :param reason: A brief summary of why the task is considered complete.
    """
    return f"Task marked as complete by the agent. Reason: {reason}"

# --- Tool Registry ---

TOOLS: Dict[str, Callable] = {
    "write_file": write_file,
    "read_file": read_file,
    "modify_file": modify_file,
    "execute_python_code": execute_python_code,
    "run_pytest": run_pytest,
    "web_search": web_search,
    "request_user_input": request_user_input,
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
