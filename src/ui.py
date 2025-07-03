import re
import pyperclip
import threading
import queue
import os
import subprocess
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from src import task_manager, workspace_manager

console = Console()
last_code_block = None
notification_queue = queue.Queue()

def _get_git_branch():
    try:
        return subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).strip().decode('utf-8')
    except Exception:
        return "not a git repo"

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

def format_and_print_thought(thought_text):
    """Processes the AI thought, detecting and formatting Markdown and code blocks."""
    console.print(Panel(Markdown(thought_text), title="Thought", border_style="yellow", expand=False))

from prompt_toolkit.formatted_text import FormattedText

def get_bottom_toolbar(agent_manager, agent_mode):
    """Generates the status bar text."""
    cwd = os.path.basename(os.getcwd())
    branch = _get_git_branch()
    model = agent_manager.model_name
    sandbox_status = "on" if workspace_manager.SANDBOX_ENABLED else "off"
    agent_status = "on" if agent_mode else "off"
    
    return FormattedText([
        ('class:toolbar.path', f"{cwd} ({branch})"),
        ('class:toolbar.separator', ' | '),
        ('class:toolbar.model', f"{model}"),
        ('class:toolbar.separator', ' | '),
        ('class:toolbar.status', f"agent: {agent_status}"),
        ('class:toolbar.separator', ' | '),
        ('class:toolbar.status', f"sandbox: {sandbox_status}"),
    ])

def start_chat_loop(agent, agent_manager=None, debug=False):
    """Handles the interactive AI chat session with command history and async tasks."""
    conversation_history = []
    session = PromptSession(history=InMemoryHistory())
    
    notification_thread = threading.Thread(target=_print_notifications, daemon=True)
    notification_thread.start()
    
    console.print("[bold green]AI Assistant Initialized. Type '/exit' or '/help'.[/bold green]", justify="center")

    while True:
        try:
            toolbar = get_bottom_toolbar(agent_manager, agent.agent_mode)
            user_input = session.prompt("\n\nYou: ", bottom_toolbar=toolbar, refresh_interval=0.5).strip()
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
                if user_input.lower() == "/sandbox":
                    workspace_manager.SANDBOX_ENABLED = not workspace_manager.SANDBOX_ENABLED
                    status = "enabled" if workspace_manager.SANDBOX_ENABLED else "disabled"
                    console.print(f"[green]Sandbox mode {status}.[/green]")
                    continue
                if user_input.lower() == "/agent":
                    agent.agent_mode = not agent.agent_mode
                    status = "enabled" if agent.agent_mode else "disabled"
                    console.print(f"[green]Agent mode {status}.[/green]")
                    continue
                if user_input.lower().startswith("/model"):
                    parts = user_input.split()
                    if len(parts) > 1:
                        model_name = parts[1]
                        agent_manager.model_name = model_name
                        console.print(f"[green]Model set to {model_name}.[/green]")
                    else:
                        console.print(f"Current model: {agent_manager.model_name}")
                    continue
                if user_input.lower() == "/models":
                    console.print("[bold]Available Models:[/bold]")
                    console.print("  - gemini-1.5-pro-latest")
                    console.print("  - gemini-1.5-flash-latest")
                    console.print("  - gemini-1.0-pro")
                    continue
                if user_input.lower() == "/help":
                    console.print("[bold]Input Mode:[/bold]")
                    console.print("  - Press [Esc] followed by [Enter] to create a newline.")
                    console.print("[bold]Available Commands:[/bold]")
                    console.print("  /exit, /quit             - Exit the application.")
                    console.print("  /copy                    - Copy the last code block.")
                    console.print("  /clear                   - Clear the conversation history.")
                    console.print("  /sandbox                 - Toggle sandbox mode.")
                    console.print("  /agent                   - Toggle agent mode.")
                    console.print("  /model <model_name>      - Switch the model.")
                    console.print("  /models                  - List available models.")
                    console.print("  /tasks                   - Instructions to open the interactive task viewer TUI.")
                    console.print("  /task_list               - List all tasks and their status.")
                    console.print("  /do <goal>               - Create and immediately start a new agent task.")
                    console.print("  /provide_input <id> <text> - Provide input to a paused task.")
                    continue

                if user_input.lower() == "/tasks":
                    console.print("\n[bold yellow]To open the Task Manager TUI, please exit the chat and run:[/bold yellow]")
                    console.print("  [cyan]python src/cli.py view[/cyan]\n")
                    continue

                if user_input.lower().startswith("/do "):
                    goal = user_input[len("/do "):
].strip()
                    task_id = task_manager.create_task(goal)
                    console.print(f"[green]✅ Task '{task_id}' created. Starting in background...[/green]")
                    task = task_manager.get_task(task_id)
                    task_thread = threading.Thread(target=agent_manager.start_task, args=(task, notification_queue))
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
                        task_thread = threading.Thread(target=agent_manager.start_task, args=(task, notification_queue))
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
            response_data = agent.handle_task(user_input, conversation_history)
            console.print(" " * 25, end="\r")
            
            thought = response_data.get("thought", "")
            response_text = response_data.get("response", "")

            conversation_history.append({"role": "user", "content": user_input})
            conversation_history.append({"role": "assistant", "content": response_data})
            
            if thought:
                format_and_print_thought(thought)

            console.print("\n[bold magenta]Assistant:[/bold magenta]")
            format_and_print_response(response_text)

        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[bold red]An unexpected error occurred in UI loop: {e}[/bold red]")
    
    notification_queue.put(None) # Signal the notification thread to exit
    console.print("[bold red]\nExiting AI Assistant...[/bold red]")
