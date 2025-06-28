import argparse
import importlib
import re
import pyperclip
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()
conversation_history = []
last_code_block = None
agents = {}

def copy_last_code():
    global last_code_block
    if last_code_block:
        pyperclip.copy(last_code_block)
        console.print("[green]✅ Code copied to clipboard![/green]")
    else:
        console.print("[yellow]⚠️ No code to copy![/yellow]")

def format_response(response_text):
    global last_code_block
    code_block_pattern = re.compile(r"```(\w+)?\n(.*?)```", re.DOTALL)
    matches = code_block_pattern.findall(response_text)

    non_code = code_block_pattern.sub("", response_text).strip()
    if non_code:
        console.print(Markdown(non_code))

    for lang, code in matches:
        lang = lang.strip() or "text"
        last_code_block = code.strip()
        syntax = Syntax(last_code_block, lang, theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title=f"Code ({lang})", expand=False))
        console.print("[dim]Type /copy to copy last code block.[/dim]\n")

def create_agent(name, base_agent):
    if name in agents:
        console.print(f"[yellow]⚠️ Agent '{name}' already exists.[/yellow]")
    else:
        agents[name] = base_agent
        console.print(f"[green]✅ Agent '{name}' created.[/green]")

def assign_task(agent_name, task):
    agent = agents.get(agent_name)
    if not agent:
        console.print(f"[red]❌ Agent '{agent_name}' not found.[/red]")
        return
    response = agent.handle_task(task, conversation_history)
    console.print(f"[cyan]{agent_name}:[/cyan] {response}")

def chat_loop(agent, token_manager):
    console.print("[bold green]Interactive Gemini AI Assistant (Type 'exit' to quit)[/bold green]", justify="center")
    while True:
        try:
            user_input = console.input("\n[bold cyan]You:[/bold cyan] ").strip()
            if user_input.lower() in ["exit", "quit"]:
                console.print("[bold red]Exiting AI Assistant...[/bold red]")
                break

            if user_input.strip() == "/copy":
                copy_last_code()
                continue

            if user_input.startswith("/create_agent "):
                name = user_input.split(" ", 1)[1].strip()
                create_agent(name, agent)
                continue

            if user_input.startswith("/assign_task "):
                try:
                    _, agent_name, task = user_input.split(" ", 2)
                    assign_task(agent_name, task)
                except ValueError:
                    console.print("[red]Usage: /assign_task <agent_name> <task>[/red]")
                continue

            response_text = agent.handle_task(user_input, conversation_history)
            conversation_history.append({"role": "assistant", "content": response_text})
            format_response(response_text)

        except KeyboardInterrupt:
            console.print("\n[bold red]Interrupted. Exiting...[/bold red]")
            break

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-a", "--enable-advanced",
        action="store_true",
        help="Enable advanced features (RAG, embeddings, full tokenization)."
    )
    args = parser.parse_args()

    if args.enable_advanced:
        agent_mod = importlib.import_module("agent_full")
        token_mod = importlib.import_module("token_manager_full")
        AgentClass = getattr(agent_mod, "RAGAgent")       # Or whatever your full agent is called
        TokenManagerClass = getattr(token_mod, "TokenManager")
        agent = AgentClass()                              # pass args as needed
        token_manager = TokenManagerClass()
        console.print("[blue]Loaded advanced agent and token manager.[/blue]")
    else:
        from agent_minimal import GeminiOnlyAgent
        from token_manager_minimal import TokenManager
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro")
        agent = GeminiOnlyAgent(llm)
        token_manager = TokenManager()
        console.print("[green]Loaded minimal agent and token manager (Termux/portable mode).[/green]")

    chat_loop(agent, token_manager)
