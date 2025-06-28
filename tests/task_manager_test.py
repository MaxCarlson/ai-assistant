import pytest
import json
from src import task_manager

@pytest.fixture(autouse=True)
def isolated_filesystem(tmp_path, monkeypatch):
    """Fixture to ensure tests don't affect the real tasks.json file."""
    # Change the current directory to a temporary one for the duration of the test
    monkeypatch.chdir(tmp_path)
    # Ensure the TASKS_FILE path points to the temporary directory
    task_manager.TASKS_FILE = tmp_path / "tasks.json"
    yield
    # The monkeypatch automatically reverts the directory change after the test

def test_create_task():
    """Tests that a task is created and saved correctly."""
    goal = "Test goal"
    task_id = task_manager.create_task(goal)
    
    assert task_id == "0"
    
    tasks = task_manager._load_tasks()
    assert task_id in tasks
    assert tasks[task_id]["goal"] == goal
    assert tasks[task_id]["status"] == "pending"

def test_get_task():
    """Tests retrieving a specific task."""
    goal = "Another test goal"
    task_id = task_manager.create_task(goal)
    
    retrieved_task = task_manager.get_task(task_id)
    assert retrieved_task is not None
    assert retrieved_task["id"] == task_id
    assert retrieved_task["goal"] == goal

def test_log_to_task():
    """Tests that logging to a task's history works."""
    task_id = task_manager.create_task("Logging test")
    log_entry = "This is a test log entry."
    
    task_manager.log_to_task(task_id, log_entry)
    
    task = task_manager.get_task(task_id)
    assert len(task["history"]) == 1
    assert task["history"][0] == log_entry

def test_update_task_status():
    """Tests that updating a task's status works."""
    task_id = task_manager.create_task("Status update test")
    
    task_manager.update_task_status(task_id, "in_progress")
    
    task = task_manager.get_task(task_id)
    assert task["status"] == "in_progress"
