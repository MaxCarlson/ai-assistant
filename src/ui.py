import re
import pyperclip
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax

# --- Global Variables ---
console = Console()
last_code_block = None

# --- UI and Helper Functions ---
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
    """
    Processes the AI response, detecting and formatting Markdown and code blocks.
    Stores the last code block for the /copy command.
    """
    global last_code_block
    last_code_block = None  # Reset for the new response

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

# --- Main Chat Loop ---
def start_chat_loop(agent):
    """Handles the interactive AI chat session."""
    conversation_history = []
    console.print("[bold green]AI Assistant Initialized. Type '/exit' to quit.[/bold green]", justify="center")

    while True:
        try:
            user_input = console.input("\n[bold cyan]You:[/bold cyan] ").strip()
            if not user_input:
                continue

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
            console.print(f"[bold red]An error occurred: {e}[/bold red]")
