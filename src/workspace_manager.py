import os
import shutil
import subprocess
import re
from pathlib import Path
from src import task_manager

def get_task_workspace(task_id: str) -> Path:
    """Gets the root directory where the agent for this task should operate."""
    task = task_manager.get_task(task_id)
    if not task:
        raise ValueError(f"Task {task_id} not found, cannot determine workspace.")
    
    # The workspace is now defined in the task itself.
    workspace_path = Path(task.get("workspace_path", ".")).expanduser().resolve()
    return workspace_path

def setup_workspace(task_id: str) -> str:
    """
    Sets up the workspace for the agent.
    If the task is configured to use a new branch, it creates one.
    Returns a status message.
    """
    task = task_manager.get_task(task_id)
    if not task:
        return "Error: Task not found."

    workspace_path = get_task_workspace(task_id)
    if not workspace_path.is_dir() or not (workspace_path / ".git").exists():
        return f"Error: Workspace path '{workspace_path}' is not a valid git repository."

    if task.get("create_branch"):
        # Sanitize goal to create a valid branch name
        sanitized_goal = re.sub(r'[^a-zA-Z0-9\-]', '_', task['goal'].lower())[:50]
        branch_name = f"agent/{task_id}-{sanitized_goal}"
        
        try:
            # Check if branch already exists
            subprocess.run(["git", "rev-parse", "--verify", branch_name], check=True, cwd=workspace_path, capture_output=True)
            # If it exists, just check it out
            subprocess.run(["git", "checkout", branch_name], check=True, cwd=workspace_path, capture_output=True)
            return f"Checked out existing branch '{branch_name}' in '{workspace_path}'"
        except subprocess.CalledProcessError:
            # Branch doesn't exist, create it
            try:
                subprocess.run(["git", "checkout", "-b", branch_name], check=True, cwd=workspace_path, capture_output=True)
                return f"Created and checked out new branch '{branch_name}' in '{workspace_path}'"
            except subprocess.CalledProcessError as e:
                return f"Error creating git branch: {e.stderr.decode()}"
    
    return f"Working in existing branch in '{workspace_path}'"

def get_safe_path(task_id: str, relative_path: str) -> Path:
    """
    Returns a safe, absolute path within the task's defined workspace.
    Prevents directory traversal attacks.
    """
    workspace_path = get_task_workspace(task_id)
    
    # os.path.normpath is crucial for security.
    normalized_relative_path = os.path.normpath(relative_path)
    
    if normalized_relative_path.startswith("..") or os.path.isabs(normalized_relative_path):
        raise PermissionError(f"Path traversal is not allowed: {relative_path}")

    safe_path = (workspace_path / normalized_relative_path).resolve()

    # Final check to ensure the resolved path is within the workspace.
    if workspace_path not in safe_path.parents and workspace_path != safe_path:
        raise PermissionError("Attempted to access file outside of workspace")
        
    return safe_path

def cleanup_workspace(task_id: str):
    """No-op in git-native mode, as we want to keep the branches."""
    print(f"Task {task_id} finished. Workspace changes are preserved in the git branch.")
