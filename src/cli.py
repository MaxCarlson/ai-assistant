import argparse
import sys
import threading
from pathlib import Path
from src import task_manager, agent_manager
from src.tui_app import TUI # Corrected: Import the TUI class directly

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

    task_id = task_manager.create_task(goal, args.tools)
    print(f"✅ Task '{task_id}' created. Starting in background...")
    
    # We don't need the queue here as we're not in the interactive UI
    agent = agent_manager.AgentManager(debug=args.debug)
    task_thread = threading.Thread(target=agent.start_task, args=(task_id,))
    task_thread.start()
    print("Agent is running. Use 'python src/cli.py list' or 'python src/cli.py view' to monitor.")

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
    app = TUI() # Corrected: Instantiate the class directly
    app.run()

def main():
    parser = argparse.ArgumentParser(description="Command-line interface for the AI agent.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 'do' command
    do_parser = subparsers.add_parser("do", help="Create and start a new task.")
    do_parser.add_argument("goal", nargs="*", help="The goal for the task.")
    do_parser.add_argument("-f", "--from-file", help="Read the task goal from a file.")
    do_parser.add_argument("-t", "--tools", nargs="+", help="Specify a list of allowed tools for this task.")
    do_parser.set_defaults(func=handle_do)

    # 'list' command
    list_parser = subparsers.add_parser("list", help="List all tasks.")
    list_parser.set_defaults(func=handle_list)

    # 'view' command
    view_parser = subparsers.add_parser("view", help="Launch the TUI to view all tasks.")
    view_parser.set_defaults(func=handle_view)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
