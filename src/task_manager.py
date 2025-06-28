import json
from pathlib import Path
from typing import List, Dict, Any, Optional

TASKS_FILE = Path("tasks.json")

def _load_tasks() -> Dict[str, Any]:
    """Loads the tasks from the JSON file."""
    if not TASKS_FILE.exists():
        return {}
    with open(TASKS_FILE, 'r') as f:
        return json.load(f)

def _save_tasks(tasks: Dict[str, Any]):
    """Saves the tasks to the JSON file."""
    with open(TASKS_FILE, 'w') as f:
        json.dump(tasks, f, indent=2)

def create_task(goal: str, max_steps: int = 15, allowed_tools: Optional[List[str]] = None) -> str:
    """Creates a new task and saves it to disk."""
    from src.tool_manager import TOOLS # Local import to avoid circular dependency
    tasks = _load_tasks()
    task_id = str(len(tasks))
    tasks[task_id] = {
        "id": task_id,
        "goal": goal,
        "history": [],
        "status": "pending",
        "max_steps": max_steps, # Added this field
        "allowed_tools": allowed_tools or list(TOOLS.keys())
    }
    _save_tasks(tasks)
    return task_id

def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single task from disk."""
    tasks = _load_tasks()
    return tasks.get(task_id)

def get_all_tasks() -> List[Dict[str, Any]]:
    """Retrieves all tasks, sorted by ID."""
    tasks = _load_tasks()
    return sorted(tasks.values(), key=lambda t: int(t['id']))

def log_to_task(task_id: str, log_entry: str):
    """Adds a log entry to a task's history."""
    tasks = _load_tasks()
    if task_id in tasks:
        tasks[task_id]["history"].append(log_entry)
        _save_tasks(tasks)

def update_task_status(task_id: str, status: str):
    """Updates the status of a task."""
    tasks = _load_tasks()
    if task_id in tasks:
        tasks[task_id]["status"] = status
        _save_tasks(tasks)
