from rich.console import Console
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
import re
import pyperclip
import keyboard  # Requires `pip install keyboard`

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from rag_manager import RAGManager
from settings import MAX_TOKENS
from token_manager import TokenManager

# Initialize Console
console = Console()

# Initialize LLM, RAG, and Token Managers
llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro")
rag_manager = RAGManager("gemini-1.5-pro", "all-MiniLM-L6-v2")
token_manager = TokenManager()

# Global variables
conversation_history = []
system_template = "You are an AI assistant. Use the following context to help answer the user's query:\n{context}\n"
last_code_block = None  # Stores the last generated code block


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
    - Adds a [c] button to copy code blocks.
    """
    global last_code_block

    # Regex pattern to detect fenced code blocks
    code_block_pattern = re.compile(r"```(\w+)?\n(.*?)```", re.DOTALL)

    matches = code_block_pattern.findall(response_text)

    if not matches:
        console.print(Markdown(response_text))
        return

    # Print non-code text
    non_code_text = code_block_pattern.sub("", response_text).strip()
    if non_code_text:
        console.print(Markdown(non_code_text))

    for lang, code in matches:
        lang = lang.lower().strip() if lang else "text"  # Default to "text"
        supported_languages = ["python", "json", "bash", "sh", "markdown", "yaml"]

        # Store code block for copying
        last_code_block = code.strip()

        if lang in supported_languages:
            syntax = Syntax(last_code_block, lang, theme="monokai", line_numbers=True)
            console.print(Panel(syntax, title=f"Code ({lang})", expand=False))
        else:
            console.print(Panel(last_code_block, title=f"Raw Code ({lang})", expand=False))

        console.print("[dim]Press [c] to Copy Code[/dim]\n")


def chat():
    """Handles the interactive AI chat session."""
    global conversation_history

    console.print("[bold green]Interactive AI Assistant (Type 'exit' to quit)[/bold green]", justify="center")

    if conversation_history is None:
        conversation_history = []  # Ensure initialization

    # Monitor for copy key (runs in background)
    keyboard.add_hotkey("c", copy_last_code)

    while True:
        try:
            user_input = console.input("\n[bold cyan]You:[/bold cyan] ").strip()
            if user_input.lower() in ["exit", "quit"]:
                console.print("[bold red]Exiting AI Assistant...[/bold red]")
                break

            # Retrieve context
            context = rag_manager.get_context(user_input, conversation_history)

            # Ensure `conversation_history` is initialized before modifying it
            if conversation_history is None:
                conversation_history = []

            # Limit tokens for conversation history and context
            conversation_history, context = token_manager.limit_tokens(
                user_input=user_input,
                conversation_history=conversation_history,
                context=context,
                max_tokens=MAX_TOKENS,
                percent_context=0.35
            )

            # Create system message
            system_message = system_template.format(context=context)
            messages = [{"role": "system", "content": system_message}]
            for entry in conversation_history:
                messages.append({"role": entry["role"], "content": entry["content"]})
            messages.append({"role": "user", "content": user_input})

            # Invoke AI
            response = llm.invoke(messages)
            conversation_history.append({"role": "assistant", "content": response.content})

            # Print formatted response
            format_response(response.content)

        except KeyboardInterrupt:
            console.print("\n[bold red]Interrupted. Exiting...[/bold red]")
            break


if __name__ == "__main__":
    chat()
