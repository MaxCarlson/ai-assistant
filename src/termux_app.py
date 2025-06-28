#!/usr/bin/env python3
"""
Entry point for the AI Assistant in minimal mode (Termux).
"""
from src.agent_minimal import MinimalAgent
from src.ui import start_chat_loop, console

if __name__ == "__main__":
    console.print("[bold blue]Initializing in Minimal Mode (for Termux/basic use)...[/bold blue]")
    try:
        # Initialize the minimal agent that uses the REST API
        agent = MinimalAgent()
        console.print("[green]✅ Minimal agent loaded.[/green]")
        
        # Start the user interface chat loop
        start_chat_loop(agent)
        
    except Exception as e:
        console.print(f"[bold red]Error initializing minimal agent: {e}[/bold red]")
        exit(1)
