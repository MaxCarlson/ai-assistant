import os
import shutil
from pathlib import Path
from src import task_manager

def get_task_workspace(task_id: str) -> Path:
    """Gets the dedicated, sandboxed directory for a task."""
    task = task_manager.get_task(task_id)
    if not task:
        # Fallback to default if task not found, though this shouldn't happen in normal flow
        base_dir = Path("workspaces").resolve()
    else:
        base_dir = Path(task.get("working_dir", "workspaces")).resolve()

    workspace_path = base_dir / task_id
    return workspace_path

def create_workspace(task_id: str):
    """Creates or cleans the dedicated directory for a task."""
    workspace_path = get_task_workspace(task_id)
    if workspace_path.exists():
        shutil.rmtree(workspace_path)
    workspace_path.mkdir(parents=True, exist_ok=True)
    print(f"Created workspace at: {workspace_path}")

def get_safe_path(task_id: str, relative_path: str) -> Path:
    """
    Returns a safe, absolute path within the task's workspace.
    Prevents directory traversal attacks.
    """
    workspace_path = get_task_workspace(task_id)
    safe_path = (workspace_path / relative_path).resolve()
    
    if workspace_path not in safe_path.parents and workspace_path != safe_path:
        raise PermissionError("Attempted to access file outside of workspace")
        
    return safe_path

def cleanup_workspace(task_id: str):
    """Deletes a task's workspace directory."""
    workspace_path = get_task_workspace(task_id)
    if workspace_path.exists():
        shutil.rmtree(workspace_path)
        print(f"Cleaned up workspace: {workspace_path}")
