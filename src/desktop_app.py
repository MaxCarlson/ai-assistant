import argparse
from src.termux_app import CLIAgent
from src.ui import start_chat_loop, console

def main():
    """
    Main entry point for the full-featured RAG agent on Desktop/WSL.
    """
    parser = argparse.ArgumentParser(description="Full-featured RAG AI Assistant")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    args = parser.parse_args()

    try:
        # This app uses the CLIAgent
        conversational_agent = CLIAgent()
        start_chat_loop(agent=conversational_agent, agent_manager=None, debug=args.debug)
    except Exception as e:
        console.print(f"[bold red]Initialization Error: {e}[/bold red]")
        console.print("[yellow]Hint: Ensure you have installed all dependencies for the RAG agent (e.g., langchain, faiss-cpu, etc.)[/yellow]")

if __name__ == "__main__":
    main()
