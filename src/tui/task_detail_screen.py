import json
import re
import threading
from textual.screen import Screen
from textual.widgets import Header, Footer, Collapsible, Markdown, Static, Input
from textual.containers import Vertical, VerticalScroll
from textual.color import Color
from rich.panel import Panel
from rich.syntax import Syntax
from src import task_manager, agent_manager

def parse_history_to_steps(history: list[str]) -> list:
    """
    Parses the flat log history into a structured list of steps.
    A "step" is defined as an AI Response followed by its corresponding Tool Result.
    """
    steps = []
    json_pattern = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)

    for i, line in enumerate(history):
        if line.startswith("AI Response:"):
            current_step = {"thought": None, "tool_call": None, "tool_result": None}
            
            match = json_pattern.search(line)
            if match:
                try:
                    response_json = json.loads(match.group(1))
                    current_step["thought"] = response_json.get("thought")
                    current_step["tool_call"] = response_json.get("tool_call")
                except json.JSONDecodeError:
                    current_step["thought"] = "Error parsing JSON in AI Response."
            
            if (i + 1) < len(history) and history[i + 1].startswith("Tool Result:"):
                current_step["tool_result"] = history[i + 1][len("Tool Result:"):].strip()
            
            steps.append(current_step)
            
    return steps


class TaskDetailScreen(Screen):
    """A screen to display the detailed, structured history of a single task."""

    def __init__(self, task_id: str):
        super().__init__()
        self.task_id = task_id
        self.displayed_lines = 0
        self._initial_message_widget = None

    def compose(self):
        yield Header(f"Task Detail - ID: {self.task_id}")
        yield VerticalScroll(id="task_log_container")
        # Add an input field, but keep it hidden initially
        yield Input(placeholder="Provide input to the agent...", id="user_input_field", disabled=True)
        yield Footer()

    def on_mount(self):
        """Load initial history and start a timer to poll for updates."""
        self.update_log()
        self.set_interval(1, self.update_log)

    def _start_resume_thread(self):
        """Helper to run the agent in a background thread."""
        agent = agent_manager.AgentManager(debug=True)
        task_thread = threading.Thread(target=agent.start_task, args=(self.task_id,))
        task_thread.daemon = True
        task_thread.start()
        self.sub_title = f"Task {self.task_id} resumed in background"

    def on_input_submitted(self, event: Input.Submitted):
        """Handle when the user presses Enter on the input field."""
        input_field = self.query_one("#user_input_field", Input)
        user_response = event.value
        
        if not user_response:
            return

        # Log the user's input, update status, and resume the agent
        task_manager.log_to_task(self.task_id, f"User Input: {user_response}")
        task_manager.update_task_status(self.task_id, "in_progress")
        self._start_resume_thread()

        # Clear and disable the input field again
        input_field.value = ""
        input_field.disabled = True
        self.set_focus(None) # Unfocus the input field

    def update_log(self) -> None:
        """Fetches the latest task history and appends new steps to the view."""
        container = self.query_one("#task_log_container")
        input_field = self.query_one("#user_input_field", Input)
        task = task_manager.get_task(self.task_id)

        if not task:
            if not self._initial_message_widget:
                self._initial_message_widget = Static("[red]Error: Task not found.[/red]")
                container.mount(self._initial_message_widget)
            return

        # Show/hide the user input field based on task status
        is_pending_input = task['status'] == 'pending_input'
        input_field.disabled = not is_pending_input
        input_field.styles.display = "block" if is_pending_input else "none"
        if is_pending_input:
            self.set_focus(input_field)

        if not task['history']:
            if not self._initial_message_widget:
                self._initial_message_widget = Static("Waiting for agent's first step...")
                container.mount(self._initial_message_widget)
            return

        if len(task['history']) == self.displayed_lines:
            return

        if self._initial_message_widget:
            self._initial_message_widget.remove()
            self._initial_message_widget = None

        container.remove_children()
        structured_history = parse_history_to_steps(task['history'])

        if not structured_history:
            container.mount(Static("[yellow]Could not parse structured steps. Displaying raw log:[/yellow]"))
            container.mount(Static("\n".join(task['history'])))
            self.displayed_lines = len(task['history'])
            return

        for i, step in enumerate(structured_history):
            step_children = [Static(f"[bold]Step {i + 1}[/bold]")]

            if step.get("thought"):
                step_children.append(
                    Collapsible(Markdown(f"> {step['thought']}"), title="View Thought")
                )
            
            if step.get("tool_call"):
                tool_call_str = json.dumps(step["tool_call"], indent=2)
                # Feature: Make the tool call collapsible
                step_children.append(
                    Collapsible(
                        Static(Syntax(tool_call_str, "json", theme="monokai", word_wrap=True)),
                        title="View Tool Call"
                    )
                )
            
            if step.get("tool_result"):
                step_children.append(
                    Static(Panel(step["tool_result"], title="Tool Result", title_align="left", border_style="green"))
                )

            step_container = Vertical(*step_children)
            step_container.styles.border = ("round", Color.parse("grey"))
            step_container.styles.margin = (1, 0)
            container.mount(step_container)

        self.displayed_lines = len(task['history'])
        container.scroll_end(animate=False)
