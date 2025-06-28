import subprocess
import os
from pathlib import Path
from typing import Callable, Dict
from src import workspace_manager

# --- Tool Implementations ---

def write_file(task_id: str, file_path: str, content: str) -> str:
    """
    Writes content to a file within the task's workspace.
    :param task_id: The ID of the current task.
    :param file_path: The relative path to the file within the workspace.
    :param content: The content to write to the file.
    """
    try:
        full_path = workspace_manager.get_workspace_path(task_id, file_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, 'w') as f:
            f.write(content)
        return f"Successfully wrote {len(content)} bytes to {file_path}"
    except Exception as e:
        return f"Error writing file: {e}"

def execute_python_code(task_id: str, file_path: str) -> str:
    """
    Executes a Python script from the task's workspace.
    :param task_id: The ID of the current task.
    :param file_path: The relative path to the Python script to execute.
    """
    try:
        full_path = workspace_manager.get_workspace_path(task_id, file_path)
        result = subprocess.run(
            ["python", str(full_path)],
            capture_output=True,
            text=True,
            timeout=30
        )
        output = f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        return output
    except Exception as e:
        return f"Error executing Python code: {e}"

def run_pytest(task_id: str) -> str:
    """
    Runs pytest within the task's workspace.
    :param task_id: The ID of the current task.
    """
    try:
        workspace_path = workspace_manager.BASE_WORKSPACE_DIR / task_id
        result = subprocess.run(
            ["pytest", str(workspace_path)],
            capture_output=True,
            text=True,
            timeout=60
        )
        output = f"PYTEST RESULTS:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        return output
    except Exception as e:
        return f"Error running pytest: {e}"

# --- Tool Registry ---

TOOLS: Dict[str, Callable] = {
    "write_file": write_file,
    "execute_python_code": execute_python_code,
    "run_pytest": run_pytest,
}

def get_tool_descriptions() -> str:
    """Generates a formatted string of tool descriptions for the LLM prompt."""
    descriptions = []
    for name, func in TOOLS.items():
        descriptions.append(f"- {name}:\n  {func.__doc__.strip()}")
    return "\n".join(descriptions)
