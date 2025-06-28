import json
import re
import threading
from textual.screen import Screen
from textual.widgets import Header, Footer, Collapsible, Markdown, Static, Input
from textual.containers import Vertical, VerticalScroll
from textual.color import Color
from textual.binding import Binding
from rich.panel import Panel
from rich.syntax import Syntax
from src import task_manager, agent_manager

def parse_history_to_steps(history: list[str]) -> list:
    """
    Parses the flat log history into a structured list of steps, where each
    step is a dictionary with a 'type' and associated data.
    """
    steps = []
    json_pattern = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
    
    i = 0
    while i < len(history):
        line = history[i]
        
        if line.startswith("User Input:"):
            steps.append({"type": "user", "content": line})
            i += 1
        elif line.startswith("---"):
            steps.append({"type": "system", "content": line})
            i += 1
        elif line.startswith("AI Response:"):
            step = {"type": "agent", "thought": None, "tool_call": None, "tool_result": None}
            match = json_pattern.search(line)
            if match:
                try:
                    response_json = json.loads(match.group(1))
                    step["thought"] = response_json.get("thought")
                    step["tool_call"] = response_json.get("tool_call")
                except json.JSONDecodeError:
                    step["thought"] = "Error parsing JSON in AI Response."
            
            if (i + 1) < len(history) and history[i + 1].startswith("Tool Result:"):
                step["tool_result"] = history[i + 1][len("Tool Result:"):].strip()
                i += 2
            else:
                i += 1
            steps.append(step)
        else:
            # Fallback for unknown lines
            i += 1
            
    return steps

class TaskDetailScreen(Screen):
    """A screen to display the detailed, structured history of a single task."""
    BINDINGS = [
        Binding("s", "start_resume_task", "Start / Resume"),
        Binding("e", "extend_task", "Extend Steps"),
        Binding("r", "redirect_task", "Redirect Goal"),
    ]

    def __init__(self, task_id: str):
        super().__init__()
        self.task_id = task_id
        self.displayed_lines = 0

    def compose(self):
        yield Header(f"Task Detail - ID: {self.task_id}")
        yield VerticalScroll(id="task_log_container")
        yield Input(placeholder="Provide input to agent...", id="user_input_field", disabled=True)
        yield Input(placeholder="Enter new goal for agent...", id="redirect_input_field", disabled=True)
        yield Footer()

    def on_mount(self):
        self.update_log()
        self.set_interval(1, self.update_log)

    def _start_resume_thread(self):
        agent = agent_manager.AgentManager(debug=True)
        task_thread = threading.Thread(target=agent.start_task, args=(self.task_id,))
        task_thread.daemon = True
        task_thread.start()
        self.sub_title = f"Task {self.task_id} resumed"

    def on_input_submitted(self, event: Input.Submitted):
        if event.input.id == "user_input_field":
            self._handle_user_input(event.value)
        elif event.input.id == "redirect_input_field":
            self._handle_redirect_input(event.value)

    def _handle_user_input(self, value: str):
        if not value: return
        self.query_one("#user_input_field", Input).disabled = True
        task_manager.log_to_task(self.task_id, f"User Input: {value}")
        task_manager.update_task_status(self.task_id, "in_progress")
        self._start_resume_thread()
        self.query_one("#user_input_field", Input).value = ""

    def _handle_redirect_input(self, value: str):
        if not value: return
        self.query_one("#redirect_input_field", Input).disabled = True
        task_manager.update_task_goal(self.task_id, value)
        task_manager.update_task_status(self.task_id, "in_progress")
        self._start_resume_thread()
        self.query_one("#redirect_input_field", Input).value = ""

    def action_start_resume_task(self):
        task = task_manager.get_task(self.task_id)
        resumable = ['pending', 'in_progress', 'failed', 'completed_max_steps']
        if task and task['status'] in resumable:
            if task['status'] == 'completed_max_steps':
                task_manager.extend_task_steps(self.task_id)
            self._start_resume_thread()

    def action_extend_task(self):
        task_manager.extend_task_steps(self.task_id)
        self.sub_title = "Task extended. Press 's' to resume."

    def action_redirect_task(self):
        self.query_one("#redirect_input_field").disabled = False
        self.query_one("#redirect_input_field").focus()
        self.sub_title = "Enter new goal and press Enter to redirect task."

    def update_log(self) -> None:
        container = self.query_one("#task_log_container")
        task = task_manager.get_task(self.task_id)
        if not task: return

        redirect_input = self.query_one("#redirect_input_field", Input)
        user_input = self.query_one("#user_input_field", Input)
        user_input.styles.display = "block" if task['status'] == 'pending_input' else "none"
        redirect_input.styles.display = "block" if not redirect_input.disabled else "none"
        if task['status'] == 'pending_input' and user_input.disabled:
            user_input.disabled = False
            user_input.focus()

        if len(task['history']) == self.displayed_lines: return
        container.remove_children()
        
        structured_history = parse_history_to_steps(task['history'])
        for i, step in enumerate(structured_history):
            children = []
            step_type = step.get("type")

            if step_type == "user":
                children.append(Static(Panel(step['content'], title="User Input", border_style="magenta")))
            elif step_type == "system":
                children.append(Static(Panel(step['content'], title="System Message", border_style="blue")))
            elif step_type == "agent":
                if step.get("thought"):
                    children.append(Collapsible(Markdown(f"> {step['thought']}"), title="View Thought"))
                if step.get("tool_call"):
                    tool_call_str = json.dumps(step["tool_call"], indent=2)
                    children.append(Collapsible(Static(Syntax(tool_call_str, "json", theme="monokai", word_wrap=True)), title="View Tool Call"))
                if step.get("tool_result"):
                    panel_color = "green"
                    if "paused" in step["tool_result"]: panel_color = "yellow"
                    children.append(Static(Panel(step["tool_result"], title="Tool Result", border_style=panel_color)))
            
            step_container = Vertical(*children)
            step_container.styles.border = ("round", Color.parse("grey"))
            step_container.styles.margin = (1, 0)
            # Fixed: Removed min_height to allow natural sizing
            step_container.styles.height = "auto" 
            step_container.border_title = f"Step {i + 1}"
            container.mount(step_container)

        self.displayed_lines = len(task['history'])
        container.scroll_end(animate=False)
