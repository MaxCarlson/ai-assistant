import asyncio
import os
import re
import subprocess

from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import FormattedText
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax

from src import task_manager, workspace_manager

console = Console()

def _get_git_branch():
    try:
        return subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).strip().decode('utf-8')
    except Exception:
        return "not a git repo"

def get_bottom_toolbar(agent_manager, agent_mode):
    """Generates the status bar text."""
    cwd = os.path.basename(os.getcwd())
    branch = _get_git_branch()
    model = agent_manager.model_name
    sandbox_status = "on" if workspace_manager.SANDBOX_ENABLED else "off"
    agent_status = "on" if agent_mode else "off"
    
    return FormattedText([
        ('bold', f" {cwd} ({branch}) "),
        ('', '|'),
        ('bold', f" {model} "),
        ('', '|'),
        ('', f" agent: {agent_status} "),
        ('', '|'),
        ('', f" sandbox: {sandbox_status} "),
    ])

def format_and_print_response(response_text):
    """Processes the AI response, detecting and formatting Markdown and code blocks."""
    code_block_pattern = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
    parts = code_block_pattern.split(response_text)
    if parts[0].strip():
        console.print(Markdown(parts[0].strip()))
    for i in range(1, len(parts), 3):
        lang = parts[i].strip().lower() or "text"
        code = parts[i+1].strip()
        syntax = Syntax(code, lang, theme="monokai", line_numbers=True, word_wrap=True)
        console.print(Panel(syntax, title=f"Code ({lang})", expand=False, border_style="blue"))
        if (i + 2) < len(parts) and parts[i+2].strip():
            console.print(Markdown(parts[i+2].strip()))

def format_and_print_thought(thought_text):
    """Processes the AI thought, detecting and formatting Markdown and code blocks."""
    console.print(Panel(Markdown(thought_text), title="Thought", border_style="yellow", expand=False))

async def start_chat_loop(agent, agent_manager=None, debug=False):
    """Handles the interactive AI chat session."""
    session = PromptSession(history=None)
    console.print("[bold green]AI Assistant Initialized. Type '/exit' or '/help'.[/bold green]", justify="center")

    while True:
        try:
            toolbar = get_bottom_toolbar(agent_manager, agent.agent_mode)
            
            user_input = await session.prompt_async(
                '> ',
                bottom_toolbar=toolbar,
                multiline=False,
            )

            if not user_input:
                continue

            if user_input.lower().startswith('/'):
                # Handle commands
                if user_input.lower() in ["/exit", "/quit"]:
                    break
                elif user_input.lower() == "/help":
                    console.print(get_help_text())
                elif user_input.lower() == "/clear":
                    console.clear()
                elif user_input.lower() == "/sandbox":
                    workspace_manager.SANDBOX_ENABLED = not workspace_manager.SANDBOX_ENABLED
                    status = "enabled" if workspace_manager.SANDBOX_ENABLED else "disabled"
                    console.print(f"Sandbox mode {status}.")
                elif user_input.lower() == "/agent":
                    agent.agent_mode = not agent.agent_mode
                    status = "enabled" if agent.agent_mode else "disabled"
                    console.print(f"Agent mode {status}.")
                else:
                    console.print(f"[red]Unknown command: {user_input}[/red]")
                continue

            console.print("[yellow]Assistant is thinking...[/yellow]", end="\r")
            response_data = await agent.handle_task(user_input, [])
            console.print(" " * 25, end="\r")
            
            thought = response_data.get("thought", "")
            response_text = response_data.get("response", "")
            
            if thought:
                format_and_print_thought(thought)

            console.print("\n[bold magenta]Assistant:[/bold magenta]")
            format_and_print_response(response_text)

        except (KeyboardInterrupt, EOFError):
            break
        except Exception as e:
            console.print(f"[bold red]An unexpected error occurred in UI loop: {e}[/bold red]")
    
    console.print("[bold red]\nExiting AI Assistant...[/bold red]")

def get_help_text():
    return """
[bold]Input Mode:[/bold]
  - Press [Enter] to send your message.
  - Press [Esc] followed by [Enter] to create a newline.
[bold]Available Commands:[/bold]
  /exit, /quit             - Exit the application.
  /clear                   - Clear the conversation history.
  /sandbox                 - Toggle sandbox mode.
  /agent                   - Toggle agent mode.
"""
