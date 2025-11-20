import os
import shutil
import subprocess
import re
from pathlib import Path
from src import task_manager

SANDBOX_ENABLED = False

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
    # Ensure the workspace directory exists
    workspace_path.mkdir(parents=True, exist_ok=True)
    
    # Set the current working directory for the agent's operations
    os.chdir(workspace_path)
    
    return f"Working in workspace: '{workspace_path}'"

def get_safe_path(task_id: str, relative_path: str) -> Path:
    """
    Returns a safe, absolute path within the task's defined workspace.
    Prevents directory traversal attacks.
    """
    workspace_path = get_task_workspace(task_id)
    
    if SANDBOX_ENABLED:
        # os.path.normpath is crucial for security.
        normalized_relative_path = os.path.normpath(relative_path)
        
        if normalized_relative_path.startswith("..") or os.path.isabs(normalized_relative_path):
            raise PermissionError(f"Path traversal is not allowed: {relative_path}")

        safe_path = (workspace_path / normalized_relative_path).resolve()

        # Final check to ensure the resolved path is within the workspace.
        if workspace_path not in safe_path.parents and workspace_path != safe_path:
            raise PermissionError("Attempted to access file outside of workspace")
            
        return safe_path
    else:
        return (workspace_path / relative_path).resolve()

def cleanup_workspace(task_id: str):
    """No-op in git-native mode, as we want to keep the branches."""
    print(f"Task {task_id} finished. Workspace changes are preserved in the git branch.")
