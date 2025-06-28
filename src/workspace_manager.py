import os
import shutil
from pathlib import Path
from src import task_manager

def get_task_workspace(task_id: str) -> Path:
    """Gets the dedicated, sandboxed directory for a task."""
    # All agent work happens in a dedicated, isolated workspace.
    base_dir = Path("workspaces").resolve()
    workspace_path = base_dir / task_id
    return workspace_path

def create_workspace(task_id: str):
    """Creates or cleans the dedicated directory for a task."""
    workspace_path = get_task_workspace(task_id)
    if workspace_path.exists():
        shutil.rmtree(workspace_path)
    workspace_path.mkdir(parents=True, exist_ok=True)
    print(f"Created workspace at: {workspace_path}")

def get_safe_path(task_id: str, relative_path: str, write_access_required: bool = False) -> Path:
    """
    Returns a safe, absolute path for a file operation.
    Prevents directory traversal attacks and enforces read-only paths.
    """
    task = task_manager.get_task(task_id)
    if not task:
        raise ValueError(f"Task {task_id} not found.")

    # Normalize the relative path to prevent traversal issues.
    # os.path.normpath is crucial here.
    normalized_relative_path = os.path.normpath(relative_path)
    if normalized_relative_path.startswith("..") or os.path.isabs(normalized_relative_path):
        raise PermissionError(f"Invalid path specified: {relative_path}")

    # By default, all operations are relative to the task's workspace.
    base_path = get_task_workspace(task_id)
    safe_path = (base_path / normalized_relative_path).resolve()

    # Final check to ensure the path is within the workspace.
    if base_path not in safe_path.parents and base_path != safe_path:
        raise PermissionError("Attempted to access file outside of workspace")

    if write_access_required:
        read_only_paths = [Path(p).resolve() for p in task.get("read_only_paths", [])]
        for read_only_path in read_only_paths:
            if read_only_path in safe_path.parents or read_only_path == safe_path:
                raise PermissionError(f"Write operation denied. Path is in a read-only directory: {relative_path}")
                
    return safe_path

def cleanup_workspace(task_id: str):
    """Deletes a task's workspace directory."""
    workspace_path = get_task_workspace(task_id)
    if workspace_path.exists():
        shutil.rmtree(workspace_path)
        print(f"Cleaned up workspace: {workspace_path}")
