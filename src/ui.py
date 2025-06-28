import re
import pyperclip
import threading
import queue
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from src import task_manager
from src.tui_app import TUI # Corrected Import

console = Console()
last_code_block = None
notification_queue = queue.Queue()

def _print_notifications():
    """A daemon thread function that prints messages from the notification queue."""
    while True:
        try:
            message = notification_queue.get()
            if message is None: # Sentinel value to stop the thread
                break
            # Using print() here to avoid conflicts with prompt_toolkit's rendering
            print(f"\n🔔 [dim yellow]{message}[/dim yellow]")
            # This is a trick to redraw the prompt line after printing
            session = PromptSession.get_app().current_buffer
            if session:
                session.redraw()
        except Exception:
            # If something goes wrong, just exit the thread silently.
            break

def copy_last_code_to_clipboard():
    """Copies the last detected code block to the clipboard."""
    global last_code_block
    if last_code_block:
        try:
            pyperclip.copy(last_code_block)
            console.print("[green]✅ Code copied to clipboard![/green]")
        except pyperclip.PyperclipException as e:
            console.print(f"[red]❌ Error copying to clipboard: {e}[/red]")
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

def start_chat_loop(agent, agent_manager=None, debug=False):
    """Handles the interactive AI chat session with command history and async tasks."""
    conversation_history = []
    session = PromptSession(history=InMemoryHistory())
    
    notification_thread = threading.Thread(target=_print_notifications, daemon=True)
    notification_thread.start()
    
    console.print("[bold green]AI Assistant Initialized. Type '/exit' or '/help'.[/bold green]", justify="center")

    while True:
        try:
            user_input = session.prompt("\n\nYou: ").strip()
            if not user_input:
                continue

            if user_input.lower().startswith('/'):
                if user_input.lower() in ["/exit", "/quit"]:
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
                    console.print("  /exit, /quit             - Exit the application.")
                    console.print("  /copy                    - Copy the last code block.")
                    console.print("  /clear                   - Clear the conversation history.")
                    console.print("  /tasks                   - Open the interactive task viewer TUI.")
                    console.print("  /task_list               - List all tasks and their status.")
                    console.print("  /do <goal>               - Create and immediately start a new agent task.")
                    console.print("  /provide_input <id> <text> - Provide input to a paused task.")
                    continue

                if user_input.lower() == "/tasks":
                    TUI().run()
                    console.print("[yellow]TUI closed. Returning to chat.[/yellow]")
                    continue

                if user_input.lower().startswith("/do "):
                    goal = user_input[len("/do "):].strip()
                    task_id = task_manager.create_task(goal)
                    console.print(f"[green]✅ Task '{task_id}' created. Starting in background...[/green]")
                    task_thread = threading.Thread(target=agent_manager.start_task, args=(task_id, notification_queue))
                    task_thread.start()
                    continue
                
                if user_input.lower().startswith("/provide_input "):
                    parts = user_input.split(" ", 2)
                    if len(parts) < 3:
                        console.print("[red]Usage: /provide_input <task_id> <your_input_text>[/red]")
                        continue
                    task_id, user_response = parts[1], parts[2]
                    task = task_manager.get_task(task_id)
                    if task and task['status'] == 'pending_input':
                        task_manager.log_to_task(task_id, f"User Input: {user_response}")
                        console.print(f"[yellow]🚀 Resuming task '{task_id}' with your input...[/yellow]")
                        task_thread = threading.Thread(target=agent_manager.start_task, args=(task_id, notification_queue))
                        task_thread.start()
                    else:
                        console.print(f"[red]Error: Task {task_id} not found or not awaiting input.[/red]")
                    continue

                if user_input.lower() == "/task_list":
                    console.print("[bold]Tasks:[/bold]")
                    tasks = task_manager.get_all_tasks()
                    if not tasks:
                        console.print("  No tasks created yet.")
                    for task in tasks:
                        console.print(f"  - ID: {task['id']} | Status: {task['status']} | Goal: {task['goal']}")
                    continue
                
                console.print(f"[red]Unknown command: {user_input}[/red]")
                continue

            # Regular chat logic
            console.print("[yellow]Assistant is thinking...[/yellow]", end="\r")
            response_text = agent.handle_task(user_input, conversation_history)
            console.print(" " * 25, end="\r")
            conversation_history.append({"role": "user", "content": user_input})
            conversation_history.append({"role": "assistant", "content": response_text})
            console.print("\n[bold magenta]Assistant:[/bold magenta]")
            format_and_print_response(response_text)

        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[bold red]An unexpected error occurred in UI loop: {e}[/bold red]")
    
    notification_queue.put(None) # Signal the notification thread to exit
    console.print("[bold red]\nExiting AI Assistant...[/bold red]")
