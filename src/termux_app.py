#!/usr/bin/env python3
"""
Entry point for the AI Assistant in minimal mode (Termux).
"""
from src.agent_minimal import MinimalAgent
from src.agent_manager import AgentManager
from src.ui import start_chat_loop, console

if __name__ == "__main__":
    console.print("[bold blue]Initializing in Minimal Mode (with Agent capabilities)...[/bold blue]")
    try:
        conversational_agent = MinimalAgent()
        console.print("[green]✅ Conversational agent loaded.[/green]")
        
        agent_manager = AgentManager()
        console.print("[green]✅ Autonomous agent manager loaded.[/green]")
        
        start_chat_loop(agent=conversational_agent, agent_manager=agent_manager)
        
    except Exception as e:
        console.print(f"[bold red]Error during initialization: {e}[/bold red]")
        exit(1)
