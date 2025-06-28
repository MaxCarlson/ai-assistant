import argparse
from src.agent_minimal import MinimalAgent
from src.agent_manager import AgentManager
from src.ui import start_chat_loop, console

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    args = parser.parse_args()

    try:
        conversational_agent = MinimalAgent()
        agent_manager = AgentManager(debug=args.debug)
        start_chat_loop(agent=conversational_agent, agent_manager=agent_manager, debug=args.debug)
    except Exception as e:
        console.print(f"[bold red]Initialization Error: {e}[/bold red]")
