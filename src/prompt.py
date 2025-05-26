#!/usr/bin/env python3
"""
A prompt_toolkit-based interactive chat interface with a scrollable,
ANSI-formatted output area and command-based copy for code blocks.
This version adds a scrollbar to the output area and global key bindings to scroll.
"""

import re
import pyperclip

from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.margins import ScrollbarMargin
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import ANSI

from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax

# Import your AI/LLM and context managers
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from rag_manager import RAGManager
from settings import MAX_TOKENS
from token_manager import TokenManager

# -----------------------------------------------------------------------------
# Globals and Initialization
# -----------------------------------------------------------------------------
llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro")
rag_manager = RAGManager("gemini-1.5-pro", "all-MiniLM-L6-v2")
token_manager = TokenManager()
conversation_history = []
system_template = (
    "You are an AI assistant. Use the following context to help answer the user's query:\n{context}\n"
)

# Global list to store code blocks (each is a string).
code_blocks = []

# Global conversation text (a string with ANSI escapes).
conversation_text = ""

# A Rich Console to render content.
console = Console()

# Global style for prompt_toolkit.
style = Style.from_dict({
    'output': 'bg:#000000 #ffffff',
    'input': 'bg:#444444 #ffffff',
})

# -----------------------------------------------------------------------------
# Helper: Render a Rich renderable to ANSI text.
# -----------------------------------------------------------------------------
def render_with_rich(renderable):
    with console.capture() as capture:
        console.print(renderable)
    return capture.get()

# -----------------------------------------------------------------------------
# Helper: Process the assistant’s response into a string.
#  - Renders non-code text as Markdown.
#  - Detects code blocks (fenced with ```lang ... ```) and renders them via Rich’s Syntax.
#  - Appends a numbered marker for each code block.
#  - Stores each code block in the global list.
# -----------------------------------------------------------------------------
def process_response_to_text(response_text):
    result = ""
    code_block_pattern = re.compile(r"```(\w+)?\n(.*?)```", re.DOTALL)
    matches = list(code_block_pattern.finditer(response_text))
    # Process non-code text.
    non_code_text = code_block_pattern.sub("", response_text).strip()
    if non_code_text:
        md = Markdown(non_code_text)
        rendered_md = render_with_rich(md)
        result += rendered_md + "\n"
    # Process each code block.
    for idx, match in enumerate(matches, start=1):
        lang = match.group(1) if match.group(1) else "text"
        code = match.group(2).strip()
        code_blocks.append(code)
        syntax = Syntax(code, lang, theme="monokai", line_numbers=True)
        rendered_code = render_with_rich(syntax)
        result += rendered_code + f"\n[Code block {idx}] <Copy>\n"
    return result

# -----------------------------------------------------------------------------
# Setup the output control.
# -----------------------------------------------------------------------------
output_control = FormattedTextControl(text=ANSI(conversation_text))
output_window = Window(
    content=output_control,
    wrap_lines=True,
    always_hide_cursor=True,
    right_margins=[ScrollbarMargin(display_arrows=True)]
)

# -----------------------------------------------------------------------------
# Setup the input field.
# -----------------------------------------------------------------------------
input_field = TextArea(
    height=3,
    prompt='You: ',
    style='class:input',
    multiline=False
)

# -----------------------------------------------------------------------------
# Key Bindings.
# -----------------------------------------------------------------------------
kb = KeyBindings()

@kb.add('c-c')
def exit_(event):
    event.app.exit()

# Global key bindings to scroll the output window.
@kb.add('pageup')
@kb.add('escape', 'up')
def scroll_up(event):
    output_window.vertical_scroll = max(0, output_window.vertical_scroll - 3)
    event.app.invalidate()

@kb.add('pagedown')
@kb.add('escape', 'down')
def scroll_down(event):
    output_window.vertical_scroll += 3
    event.app.invalidate()

# -----------------------------------------------------------------------------
# Handler for when the user presses Enter.
# -----------------------------------------------------------------------------
def handle_enter(buff):
    global conversation_text
    user_input = input_field.text.strip()
    input_field.text = ""  # Clear input field.
    
    # Command: /clear resets the conversation.
    if user_input == "/clear":
        conversation_text = ""
        conversation_history.clear()
        code_blocks.clear()
        output_control.text = ANSI(conversation_text)
        app.invalidate()
        return
    
    # Command: /copy <n> copies the nth code block.
    if user_input.startswith("/copy"):
        parts = user_input.split()
        if len(parts) == 2 and parts[1].isdigit():
            idx = int(parts[1])
            if 1 <= idx <= len(code_blocks):
                pyperclip.copy(code_blocks[idx - 1])
                conversation_text += f"\x1b[32m[Status] Code block {idx} copied to clipboard!\x1b[0m\n"
            else:
                conversation_text += "\x1b[31m[Error] Invalid code block number!\x1b[0m\n"
        else:
            conversation_text += "\x1b[31m[Error] Usage: /copy <code_block_number>\x1b[0m\n"
        output_control.text = ANSI(conversation_text)
        app.invalidate()
        return

    # Append user's message.
    conversation_text += f"\x1b[36mYou:\x1b[0m {user_input}\n"
    
    # Prepare messages for the LLM.
    context = rag_manager.get_context(user_input, conversation_history)
    conversation_history_mod, context = token_manager.limit_tokens(
        user_input=user_input,
        conversation_history=conversation_history,
        context=context,
        max_tokens=MAX_TOKENS,
        percent_context=0.35
    )
    system_message = system_template.format(context=context)
    messages = [{"role": "system", "content": system_message}]
    for entry in conversation_history:
        messages.append({"role": entry["role"], "content": entry["content"]})
    messages.append({"role": "user", "content": user_input})
    
    # Invoke the LLM.
    response = llm.invoke(messages)
    conversation_history.append({"role": "assistant", "content": response.content})
    
    # Append assistant's header and response.
    conversation_text += f"\x1b[32mAssistant:\x1b[0m\n"
    response_text = process_response_to_text(response.content)
    conversation_text += response_text + "\n"
    
    # Update the output control.
    output_control.text = ANSI(conversation_text)
    app.invalidate()

# Set the accept_handler.
input_field.accept_handler = handle_enter

# -----------------------------------------------------------------------------
# Create the root layout.
# -----------------------------------------------------------------------------
root_container = HSplit([
    output_window,
    input_field,
])
layout = Layout(root_container, focused_element=input_field)

# -----------------------------------------------------------------------------
# Create and run the application.
# -----------------------------------------------------------------------------
app = Application(layout=layout, key_bindings=kb, full_screen=True, style=style)

if __name__ == "__main__":
    app.run()

