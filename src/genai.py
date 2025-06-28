#!/usr/bin/env python3
"""
Entry point for the AI Assistant in advanced RAG mode (WSL2/Desktop).
"""
from src.agent_full import RAGAgent
from src.agent_manager import AgentManager
from src.ui import start_chat_loop, console

if __name__ == "__main__":
    console.print("[bold blue]Initializing in Advanced Mode (with RAG and Agent capabilities)...[/bold blue]")
    try:
        # Initialize the conversational agent
        conversational_agent = RAGAgent()
        console.print("[green]✅ Conversational RAG agent loaded.[/green]")
        
        # Initialize the autonomous agent manager
        agent_manager = AgentManager()
        console.print("[green]✅ Autonomous agent manager loaded.[/green]")

        # Start the user interface chat loop, passing both agents
        start_chat_loop(agent=conversational_agent, agent_manager=agent_manager)

    except ImportError as e:
        console.print(f"[bold red]Error: Failed to import modules for advanced mode: {e}[/red]")
        console.print("[yellow]Please ensure all dependencies like 'transformers', 'faiss-cpu', and 'pytest' are installed.[/yellow]")
        exit(1)
    except Exception as e:
        console.print(f"[bold red]Error initializing advanced agent: {e}[/bold red]")
        exit(1)
