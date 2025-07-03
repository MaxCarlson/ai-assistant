import argparse
from src.termux_app import CLIAgent
from src.agent_manager import AgentManager
from src.ui import start_chat_loop, console
from src import cli_handler # Renamed from cli

def main():
    parser = argparse.ArgumentParser(
        description="AI Assistant with Conversational, CLI, and TUI modes."
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug logging for agents."
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # If no command is given, default to chat mode.
    parser.set_defaults(func=lambda args: run_chat(args))

    # 'do' command
    do_parser = subparsers.add_parser("do", help="Create and start a new task.")
    do_parser.add_argument("goal", nargs="*", help="The goal for the task.")
    do_parser.add_argument("-f", "--from-file", help="Read the task goal from a file.")
    do_parser.add_argument("-t", "--tools", nargs="+", help="Specify a list of allowed tools for this task.")
    do_parser.set_defaults(func=cli_handler.handle_do)

    # 'list' command
    list_parser = subparsers.add_parser("list", help="List all tasks.")
    list_parser.set_defaults(func=cli_handler.handle_list)

    # 'view' command
    view_parser = subparsers.add_parser("view", help="Launch the TUI to view all tasks.")
    view_parser.set_defaults(func=cli_handler.handle_view)
    
    # 'chat' command (explicitly)
    chat_parser = subparsers.add_parser("chat", help="Start the interactive chat mode.")
    chat_parser.set_defaults(func=lambda args: run_chat(args))

    args = parser.parse_args()
    args.func(args)

def run_chat(args):
    """Initializes and starts the conversational chat loop."""
    try:
        conversational_agent = CLIAgent()
        start_chat_loop(agent=conversational_agent, agent_manager=None, debug=args.debug)
    except Exception as e:
        console.print(f"[bold red]Initialization Error: {e}[/bold red]")

if __name__ == "__main__":
    main()
