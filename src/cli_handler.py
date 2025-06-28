import sys
import threading
from pathlib import Path
from src import task_manager, agent_manager
from src.tui_app import TUI

def handle_do(args):
    """Handles the 'do' command."""
    if args.from_file:
        try:
            goal = Path(args.from_file).read_text()
        except FileNotFoundError:
            print(f"Error: File not found at {args.from_file}")
            sys.exit(1)
    elif args.goal:
        goal = " ".join(args.goal)
    else:
        print("Error: 'do' command requires a goal or a --from-file argument.")
        sys.exit(1)

    tools = args.tools if hasattr(args, 'tools') and args.tools else None
    task_id = task_manager.create_task(goal, allowed_tools=tools)
    print(f"✅ Task '{task_id}' created. Starting in background...")
    
    agent = agent_manager.AgentManager(debug=args.debug)
    task_thread = threading.Thread(target=agent.start_task, args=(task_id,))
    task_thread.daemon = True
    task_thread.start()
    print("Agent is running. Use 'python src/main.py view' to monitor.")

def handle_list(args):
    """Handles the 'list' command."""
    tasks = task_manager.get_all_tasks()
    if not tasks:
        print("No tasks found.")
        return
    for task in tasks:
        print(f"ID: {task['id']} | Status: {task['status']} | Goal: {task['goal'][:70]}...")

def handle_view(args):
    """Handles the 'view' command by launching the TUI."""
    app = TUI()
    app.run()
