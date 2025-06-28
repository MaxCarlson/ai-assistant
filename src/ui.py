import re
import pyperclip
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory

console = Console()
last_code_block = None

def copy_last_code_to_clipboard():
    """Copies the last detected code block to the clipboard."""
    global last_code_block
    if last_code_block:
        try:
            pyperclip.copy(last_code_block)
            console.print("[green]✅ Code copied to clipboard![/green]")
        except pyperclip.PyperclipException as e:
            console.print(f"[red]❌ Error copying to clipboard: {e}[/red]")
            console.print("[yellow]Tip: On Termux, you may need to run 'pkg install termux-api'[/yellow]")
    else:
        console.print("[yellow]⚠️ No code block in the last response to copy.[/yellow]")

def format_and_print_response(response_text):
    """Processes the AI response, detecting and formatting Markdown and code blocks."""
    global last_code_block
    last_code_block = None
    code_block_pattern = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
    parts = code_block_pattern.split(response_text)
    if parts[0].strip():
        console.print(Markdown(parts[0].strip()))
    for i in range(1, len(parts), 3):
        lang = parts[i].strip().lower() or "text"
        code = parts[i+1].strip()
        last_code_block = code
        syntax = Syntax(code, lang, theme="monokai", line_numbers=True, word_wrap=True)
        console.print(Panel(syntax, title=f"Code ({lang})", expand=False, border_style="blue"))
        if (i + 2) < len(parts) and parts[i+2].strip():
            console.print(Markdown(parts[i+2].strip()))
    if last_code_block:
        console.print("\n[dim]Type '/copy' to copy the last code block to the clipboard.[/dim]")

def start_chat_loop(agent, agent_manager=None):
    """Handles the interactive AI chat session with command history."""
    conversation_history = []
    session = PromptSession(history=InMemoryHistory())
    
    console.print("[bold green]AI Assistant Initialized. Type '/exit' to quit or '/help' for commands.[/bold green]", justify="center")

    while True:
        try:
            user_input = session.prompt("\n\nYou: ").strip()
            if not user_input:
                continue

            if user_input.lower().startswith('/'):
                if user_input.lower() in ["/exit", "/quit"]:
                    console.print("[bold red]Exiting AI Assistant...[/bold red]")
                    break
                if user_input.lower() == "/copy":
                    copy_last_code_to_clipboard()
                    continue
                if user_input.lower() == "/clear":
                    conversation_history.clear()
                    console.print("[yellow]🧹 Conversation history cleared.[/yellow]")
                    continue
                if user_input.lower() == "/help":
                    console.print("[bold]Available Commands:[/bold]")
                    console.print("  /exit, /quit        - Exit the application.")
                    console.print("  /copy               - Copy the last code block.")
                    console.print("  /clear              - Clear the conversation history.")
                    console.print("  /task_create <goal> - Create a new agent task.")
                    console.print("  /task_start <id>    - Start a created task (e.g., /task_start 0).")
                    console.print("  /do <goal>          - Create and immediately start a new agent task.")
                    console.print("  /task_list          - List all tasks and their status.")
                    continue

                # New: /do command
                if user_input.lower().startswith("/do "):
                    goal = user_input[len("/do "):].strip()
                    console.print(f"[green]✅ Creating and starting task with goal: {goal}[/green]")
                    task_id = agent_manager.create_task(goal)
                    console.print(f"[yellow]🚀 Starting task '{task_id}'...[/yellow]")
                    result = agent_manager.start_task(task_id)
                    console.print(f"[green]✅ {result}[/green]")
                    continue
                
                if user_input.lower().startswith("/task_create "):
                    goal = user_input[len("/task_create "):].strip()
                    task_id = agent_manager.create_task(goal)
                    console.print(f"[green]✅ Task '{task_id}' created with goal: {goal}[/green]")
                    continue
                if user_input.lower().startswith("/task_start "):
                    task_id = user_input[len("/task_start "):].strip().strip("'\"")
                    console.print(f"[yellow]🚀 Starting task '{task_id}'...[/yellow]")
                    result = agent_manager.start_task(task_id)
                    console.print(f"[green]✅ {result}[/green]")
                    continue
                if user_input.lower() == "/task_list":
                    console.print("[bold]Tasks:[/bold]")
                    if not agent_manager.tasks:
                        console.print("  No tasks created yet.")
                    for task_id, task_info in agent_manager.tasks.items():
                        console.print(f"  - ID: {task_id} | Status: {task_info['status']} | Goal: {task_info['goal']}")
                    continue
                
                console.print(f"[red]Unknown command: {user_input}[/red]")
                continue

            console.print("[yellow]Assistant is thinking...[/yellow]", end="\r")
            response_text = agent.handle_task(user_input, conversation_history)
            console.print(" " * 25, end="\r")
            conversation_history.append({"role": "user", "content": user_input})
            conversation_history.append({"role": "assistant", "content": response_text})
            console.print("\n[bold magenta]Assistant:[/bold magenta]")
            format_and_print_response(response_text)

        except KeyboardInterrupt:
            console.print("\n[bold red]Interrupted. Exiting...[/bold red]")
            break
        except Exception as e:
            console.print(f"[bold red]An unexpected error occurred: {e}[/bold red]")
