import os
import shutil
from pathlib import Path

BASE_WORKSPACE_DIR = Path("workspaces")

def create_workspace(task_id: str) -> Path:
    """Creates a dedicated, sandboxed directory for a task."""
    workspace_path = BASE_WORKSPACE_DIR / task_id
    if workspace_path.exists():
        shutil.rmtree(workspace_path)
    workspace_path.mkdir(parents=True, exist_ok=True)
    print(f"Created workspace at: {workspace_path.resolve()}")
    return workspace_path

def get_workspace_path(task_id: str, relative_path: str) -> Path:
    """
    Returns a safe, absolute path within the task's workspace.
    Prevents directory traversal attacks.
    """
    workspace_path = BASE_WORKSPACE_DIR / task_id
    # Path.resolve() is important for security to prevent '..' traversal
    safe_path = (workspace_path / relative_path).resolve()
    
    # Ensure the resolved path is still within the workspace directory
    if workspace_path.resolve() not in safe_path.parents and workspace_path.resolve() != safe_path:
        raise PermissionError("Attempted to access file outside of workspace")
        
    return safe_path

def cleanup_workspace(task_id: str):
    """Deletes a task's workspace directory."""
    workspace_path = BASE_WORKSPACE_DIR / task_id
    if workspace_path.exists():
        shutil.rmtree(workspace_path)
        print(f"Cleaned up workspace: {workspace_path.resolve()}")
