import subprocess
import os
import sys
import re
import requests
import json
from pathlib import Path
from typing import Callable, Dict, List, Any, Optional

from src import workspace_manager

# --- Tool Implementations ---

def write_file(task_id: str, file_path: str, content: str) -> str:
    """
    Writes content to a new or existing file in the task's workspace, overwriting it completely.

    Use this tool to:
    - Create a new file from scratch.
    - Completely replace the contents of an existing file.

    CRITICAL: For making small, targeted changes to an existing file (e.g., fixing a single line of code),
    you MUST use the `modify_file` tool instead, as it is safer and more precise.

    Args:
        task_id (str): The ID of the current task.
        file_path (str): The relative path to the file within the workspace (e.g., 'src/main.py').
        content (str): The entire string content to write to the file.
    """
    if task_id is None:
        return "Error: task_id is a required argument for write_file."
    try:
        full_path = workspace_manager.get_safe_path(task_id, file_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote {len(content)} characters to {file_path}"
    except Exception as e:
        return f"Error writing file: {e}"

def read_file(task_id: str, file_path: str) -> str:
    """
    Reads the entire content of a specified file from the task's workspace and returns it as a string.

    Use this tool to:
    - Examine the contents of a file to understand its purpose, logic, or structure.
    - Get the necessary context before using `modify_file` or `write_file`.
    - Verify the result of a previous file operation.

    Args:
        task_id (str): The ID of the current task.
        file_path (str): The relative path to the file within the workspace (e.g., 'src/main.py').
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
    Modifies a file in the workspace with a series of precise operations (replace, delete, append).

    This is the PREFERRED tool for making targeted changes to existing code.
    It is less error-prone than rewriting the entire file with `write_file`.

    Example of a `changes` list:
    [
        { "action": "replace", "line_number": 15, "new_content": "    return x * y" },
        { "action": "delete", "line_number": 22 },
        { "action": "append", "content": "# New function added at the end" }
    ]

    Args:
        task_id (str): The ID of the current task.
        file_path (str): The relative path to the file to modify.
        changes (List[Dict[str, Any]]): A list of dictionaries, each specifying a single change operation.
                                         Line numbers are 1-based.
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
    Executes a Python script from the task's workspace and captures its STDOUT and STDERR.

    CRITICAL: This tool can only execute an existing file. It CANNOT execute raw Python code directly.
    You must first write the code to a file using `write_file` and then execute it using this tool.

    Args:
        task_id (str): The ID of the current task.
        file_path (str): The relative path to the Python script to execute (e.g., 'src/main.py').
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
    Runs the pytest test suite within the task's workspace and returns the results.

    This tool automatically handles the PYTHONPATH, so you do not need to worry about module import issues
    related to the workspace structure. If you encounter a `ModuleNotFoundError`, it means the `import`
    statement within your test file is incorrect. Use `read_file` and `modify_file` to fix the test code.

    Args:
        task_id (str): The ID of the current task.
        args (Optional[List[str]]): A list of command-line arguments to pass to pytest (e.g., ['-v', 'tests/']).
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
    Performs a web search using the DuckDuckGo search engine to find information on the internet.

    Use this tool when you need to:
    - Find information about a library, API, or programming concept.
    - Look up error messages or solutions to technical problems.
    - Gather general knowledge to help inform your plan to solve the user's goal.

    Args:
        query (str): The search query.
        num_results (int): The maximum number of search results to return.
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
    Pauses the current task and asks the user for clarification or additional information.

    Use this tool ONLY when you are blocked and cannot proceed without input from the user.
    For example, if the user's request is ambiguous or you need them to make a decision.

    Args:
        task_id (str): The ID of the current task.
        question (str): The specific question you need to ask the user.
    """
    return f"Task paused. User was asked: {question}"

def task_complete(task_id: str, reason: str, data: Optional[str] = None, last_tool_output: Optional[str] = None) -> str:
    """
    Marks the current task as complete. Call this tool ONLY when the user's request has been fully satisfied.

    CRITICAL: Do not use this tool if you have only completed a part of the task or if you are unsure
    if the user's goal has been met. Always confirm the work is done before calling this.

    Args:
        task_id (str): The ID of the current task.
        reason (str): A brief, one-sentence summary of how you completed the task.
        data (Optional[str]): A string containing any final data to be returned to the user (e.g., a code block).
        last_tool_output (Optional[str]): The output of the last tool that was run.
    """
    response = f"Task marked as complete by the agent. Reason: {reason}"
    if data:
        response += f"\n\n{data}"
    elif last_tool_output:
        response += f"\n\n{last_tool_output}"
    return response



def run_shell_command(task_id: str, command: str) -> str:
    """
    Executes an arbitrary shell command in the task's workspace.

    CRITICAL: This tool is powerful and can have unintended consequences.
    Use it with caution. It is best used for simple commands like `ls`, `cat`, or `echo`.
    For more complex operations, consider using more specific tools.

    Args:
        task_id (str): The ID of the current task.
        command (str): The shell command to execute.
    """
    if task_id is None:
        return "Error: task_id is a required argument for run_shell_command."
    try:
        workspace_dir = workspace_manager.get_task_workspace(task_id)
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=workspace_dir
        )
        return f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    except Exception as e:
        return f"Error executing shell command: {e}"

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
    "run_shell_command": run_shell_command,
}

def get_tool_descriptions(allowed_tools: List[str]) -> str:
    """Generates a formatted string of descriptions for the allowed tools."""
    descriptions = []
    for name in allowed_tools:
        if name in TOOLS:
            func = TOOLS[name]
            doc_lines = [line.strip() for line in func.__doc__.strip().split('\n')]
            formatted_doc = "\n  ".join(doc_lines)
            
            if workspace_manager.SANDBOX_ENABLED and name in ["write_file", "read_file", "modify_file", "execute_python_code", "run_shell_command", "run_pytest"]:
                formatted_doc += "\n  **[SANDBOX] Note: This tool is restricted to the workspace directory.**"

            descriptions.append(f"- {name}:\n  {formatted_doc}")
    return "\n".join(descriptions)
