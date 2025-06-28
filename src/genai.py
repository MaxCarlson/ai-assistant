import os
import google.generativeai as genai
from rich.console import Console
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.panel import Panel
# from rich.prompt import Prompt # Not used in this version of genai.py
import re
import pyperclip
# import keyboard # Requires `pip install keyboard` - REMOVING THIS

from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain_core.prompts import ChatPromptTemplate # Not directly used
from rag_manager import RAGManager
from settings import MAX_TOKENS
from token_manager import TokenManager

# Configure the Google API key
api_key = os.getenv('GOOGLE_API_KEY_AI_ASSISTANT')
if api_key:
    genai.configure(api_key=api_key)
else:
    print("Warning: GOOGLE_API_KEY_AI_ASSISTANT environment variable not found. Attempting to use Application Default Credentials.")

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


def copy_last_code_to_clipboard(): # Renamed to avoid conflict if user types 'copy_last_code'
    """Copies the last detected code block to the clipboard."""
    global last_code_block
    if last_code_block:
        try:
            pyperclip.copy(last_code_block)
            console.print("[green]✅ Code copied to clipboard![/green]")
        except pyperclip.PyperclipException as e:
            console.print(f"[red]❌ Error copying to clipboard: {e}[/red]")
            console.print("[yellow]📋 Last code block was:\n[/yellow]" + last_code_block)
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
    last_code_block = None # Reset at the beginning of formatting a new response

    code_block_pattern = re.compile(r"```(\w+)?\n(.*?)```", re.DOTALL)
    parts = code_block_pattern.split(response_text)
    
    # Handle the case where the response starts with a code block or has no leading text
    idx = 0
    if parts[0].strip(): # Print initial non-code text if any
        console.print(Markdown(parts[0].strip()))
    idx += 1

    while idx < len(parts):
        lang = parts[idx].lower().strip() if parts[idx] else "text"
        code = parts[idx+1].strip()
        
        last_code_block = code # Store the most recent code block

        supported_languages = ["python", "json", "bash", "sh", "markdown", "yaml", "javascript", "html", "css", "sql", "java", "c", "cpp", "csharp", "go", "ruby", "php", "swift", "kotlin", "rust", "typescript", "text"]

        if lang in supported_languages:
            syntax = Syntax(last_code_block, lang, theme="monokai", line_numbers=True)
            console.print(Panel(syntax, title=f"Code ({lang})", expand=False, border_style="blue"))
        else:
            console.print(Panel(last_code_block, title=f"Raw Code ({lang})", expand=False, border_style="blue"))
        
        console.print("[dim]Type 'copy' to copy the above code block to clipboard.[/dim]\n")

        idx += 2
        if idx < len(parts) and parts[idx].strip(): # Print subsequent non-code text if any
            console.print(Markdown(parts[idx].strip()))
        idx +=1


def chat():
    """Handles the interactive AI chat session."""
    global conversation_history

    console.print("[bold green]Interactive AI Assistant (Type 'exit' or 'quit' to exit; 'copy' to copy last code block)[/bold green]", justify="center")

    if conversation_history is None:
        conversation_history = []

    # keyboard.add_hotkey("c", copy_last_code) # REMOVING THIS LINE

    while True:
        try:
            user_input = console.input("\n[bold cyan]You:[/bold cyan] ").strip()
            if user_input.lower() in ["exit", "quit"]:
                console.print("[bold red]Exiting AI Assistant...[/bold red]")
                break
            
            if user_input.lower() == "copy":
                copy_last_code_to_clipboard()
                continue

            # Retrieve context
            context = rag_manager.get_context(user_input, conversation_history)

            if conversation_history is None: # Should be redundant due to init above, but safe
                conversation_history = []

            conversation_history, context = token_manager.limit_tokens(
                user_input=user_input,
                conversation_history=conversation_history,
                context=context,
                max_tokens=MAX_TOKENS,
                percent_context=0.35
            )

            system_message = system_template.format(context=context)
            messages = [{"role": "system", "content": system_message}]
            for entry in conversation_history: # Add previous history
                messages.append({"role": entry["role"], "content": entry["content"]})
            messages.append({"role": "user", "content": user_input})

            # Invoke AI
            console.print("[yellow]Assistant is thinking...[/yellow]")
            response = llm.invoke(messages)
            
            # Add current interaction to history
            conversation_history.append({"role": "user", "content": user_input}) # Add user input to history
            conversation_history.append({"role": "assistant", "content": response.content})


            console.print("\n[bold magenta]Assistant:[/bold magenta]")
            format_response(response.content)

        except KeyboardInterrupt:
            console.print("\n[bold red]Interrupted. Exiting...[/bold red]")
            break
        except Exception as e:
            console.print(f"[bold red]An error occurred: {e}[/bold red]")
            # break # Optionally break on other errors


if __name__ == "__main__":
    chat()