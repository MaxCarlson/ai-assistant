import argparse
from src.agent_full import RAGAgent
from src.agent_manager import AgentManager
from src.ui import start_chat_loop, console

def main():
    """
    Main entry point for the full-featured RAG agent on Desktop/WSL.
    """
    parser = argparse.ArgumentParser(description="Full-featured RAG AI Assistant")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    args = parser.parse_args()

    try:
        # This app uses the RAGAgent
        conversational_agent = RAGAgent()
        agent_manager = AgentManager(debug=args.debug)
        start_chat_loop(agent=conversational_agent, agent_manager=agent_manager, debug=args.debug)
    except Exception as e:
        console.print(f"[bold red]Initialization Error: {e}[/bold red]")
        console.print("[yellow]Hint: Ensure you have installed all dependencies for the RAG agent (e.g., langchain, faiss-cpu, etc.)[/yellow]")

if __name__ == "__main__":
    main()
