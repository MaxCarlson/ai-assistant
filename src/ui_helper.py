from rich.console import Console
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.panel import Panel
import pyperclip
import re
import readchar
import threading

console = Console()
last_code_block = None  # Stores the last detected code block


def copy_last_code():
    """Copies the last detected code block to the clipboard."""
    global last_code_block
    if last_code_block:
        pyperclip.copy(last_code_block)
        console.print("[green]✅ Code copied to clipboard![/green]")
    else:
        console.print("[yellow]⚠️ No code to copy![/yellow]")


def format_response(response_text):
    """
    Processes the AI response, detecting and formatting Markdown and code blocks properly.
    - Highlights Python, JSON, Bash, Markdown, etc.
    - Displays Markdown properly.
    - Stores the last code block for copying.
    """
    global last_code_block

    code_block_pattern = re.compile(r"```(\w+)?\n(.*?)```", re.DOTALL)
    matches = code_block_pattern.findall(response_text)

    if not matches:
        console.print(Markdown(response_text))
        return

    non_code_text = code_block_pattern.sub("", response_text).strip()
    if non_code_text:
        console.print(Markdown(non_code_text))

    for lang, code in matches:
        lang = lang.lower().strip() if lang else "text"
        supported_languages = ["python", "json", "bash", "sh", "markdown", "yaml"]

        last_code_block = code.strip()

        if lang in supported_languages:
            syntax = Syntax(last_code_block, lang, theme="monokai", line_numbers=True)
            console.print(Panel(syntax, title=f"Code ({lang})", expand=False))
        else:
            console.print(Panel(last_code_block, title=f"Raw Code ({lang})", expand=False))

        console.print("[dim]Press 'c' to Copy Code[/dim]\n")


def listen_for_copy():
    """Listens for 'c' key to copy the last code block."""
    console.print("[dim]Press 'c' to Copy Last Code Block[/dim]")
    while True:
        key = readchar.readkey()
        if key.lower() == "c":
            copy_last_code()
