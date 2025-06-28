import json
from pathlib import Path
from typing import List, Dict, Any, Optional

TASKS_FILE = Path("tasks.json")

def _load_tasks() -> Dict[str, Any]:
    """Loads the tasks from the JSON file."""
    if not TASKS_FILE.exists():
        return {}
    try:
        with open(TASKS_FILE, 'r') as f:
            content = f.read()
            if not content:
                return {}
            return json.loads(content)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def _save_tasks(tasks: Dict[str, Any]):
    """Saves the tasks to the JSON file."""
    with open(TASKS_FILE, 'w') as f:
        json.dump(tasks, f, indent=2)

def create_task(
    goal: str, 
    max_steps: int = 15, 
    allowed_tools: Optional[List[str]] = None,
    working_dir: Optional[str] = None
) -> str:
    """Creates a new task and saves it to disk."""
    from src.tool_manager import TOOLS
    tasks = _load_tasks()
    next_id = 0
    if tasks:
        next_id = max(int(k) for k in tasks.keys()) + 1
    
    task_id = str(next_id)
    tasks[task_id] = {
        "id": task_id,
        "goal": goal,
        "history": [],
        "status": "pending",
        "max_steps": max_steps,
        "allowed_tools": allowed_tools or list(TOOLS.keys()),
        "working_dir": working_dir or str(Path("workspaces").resolve()),
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
    if not tasks:
        return []
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

def delete_task(task_id: str):
    """Deletes a task from the JSON file."""
    tasks = _load_tasks()
    if task_id in tasks:
        del tasks[task_id]
        _save_tasks(tasks)

def extend_task_steps(task_id: str, additional_steps: int = 15):
    """Adds more steps to a task and resets its status to be resumed."""
    tasks = _load_tasks()
    if task_id in tasks:
        tasks[task_id]["max_steps"] += additional_steps
        if tasks[task_id]["status"] == "completed_max_steps":
            tasks[task_id]["status"] = "in_progress"
        log_to_task(task_id, f"--- Task extended by {additional_steps} steps. ---")
        _save_tasks(tasks)

def update_task_goal(task_id: str, new_goal: str):
    """Updates the goal of a task and logs the change."""
    tasks = _load_tasks()
    if task_id in tasks:
        original_goal = tasks[task_id]['goal']
        tasks[task_id]['goal'] = new_goal
        log_to_task(task_id, f"--- User redirected task. Original goal: '{original_goal}' ---")
        log_to_task(task_id, f"--- New goal: '{new_goal}' ---")
        _save_tasks(tasks)
