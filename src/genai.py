#!/usr/bin/env python3
"""
Entry point for the AI Assistant in advanced RAG mode (WSL2/Desktop).
"""
from src.agent_full import RAGAgent
from src.ui import start_chat_loop, console

if __name__ == "__main__":
    console.print("[bold blue]Initializing in Advanced Mode (with RAG)...[/bold blue]")
    try:
        # Initialize the full RAG agent
        agent = RAGAgent()
        console.print("[green]✅ Advanced RAG agent loaded.[/green]")

        # Start the user interface chat loop
        start_chat_loop(agent)

    except ImportError as e:
        console.print(f"[bold red]Error: Failed to import modules for advanced mode: {e}[/red]")
        console.print("[yellow]Please ensure all dependencies like 'transformers' and 'faiss-cpu' are installed.[/yellow]")
        exit(1)
    except Exception as e:
        console.print(f"[bold red]Error initializing advanced agent: {e}[/bold red]")
        exit(1)
