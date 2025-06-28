import json
import re
import threading
import shutil
from pathlib import Path
from textual.screen import Screen
from textual.widgets import Header, Footer, Collapsible, Markdown, Static, Input
from textual.containers import Vertical, VerticalScroll
from textual.color import Color
from textual.binding import Binding
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.markup import escape
from src import task_manager, agent_manager, workspace_manager
from .code_view_screen import CodeViewScreen

def parse_history_to_steps(history: list[str]) -> list:
    """
    Parses the flat log history into a structured list of steps, where each
    step is a dictionary with a 'type' and associated data.
    """
    steps = []
    i = 0
    json_pattern = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
    
    while i < len(history):
        line = history[i]
        
        if line.startswith("User Input:") or line.startswith("---"):
            steps.append({"type": "system", "content": line})
            i += 1
        elif line.startswith("AI Response:"):
            step = {"type": "agent", "thought": None, "tool_call": None, "tool_result": None, "diff": None}
            match = json_pattern.search(line)
            if match:
                try:
                    response_json = json.loads(match.group(1))
                    step["thought"] = response_json.get("thought")
                    step["tool_call"] = response_json.get("tool_call")
                except json.JSONDecodeError:
                    step["thought"] = "Error parsing JSON in AI Response."
            
            if (i + 1) < len(history) and history[i + 1].startswith("Tool Result:"):
                result_line = history[i + 1][len("Tool Result:"):].strip()
                try:
                    # Try to parse the result as JSON for structured data (summary, diff)
                    result_data = json.loads(result_line)
                    step["tool_result"] = result_data.get("summary", result_line)
                    step["diff"] = result_data.get("diff")
                except json.JSONDecodeError:
                    # Fallback for old, plain-text results
                    step["tool_result"] = result_line
                i += 2
            else:
                i += 1
            steps.append(step)
        else:
            # Handle unstructured lines, like old error messages
            if "Error processing step:" in line:
                 steps.append({"type": "system", "content": line})
            i += 1
            
    return steps

class TaskDetailScreen(Screen):
    """A screen to display the detailed, structured history of a single task."""
    BINDINGS = [
        Binding("s", "start_resume_task", "Start/Resume"),
        Binding("e", "extend_task", "Extend"),
        Binding("r", "redirect_task", "Redirect"),
        Binding("v", "view_code", "View Code"),
        Binding("x", "export_log", "Export Log"),
        Binding("X", "export_all", "Export All"),
    ]

    def __init__(self, task_id: str):
        super().__init__()
        self.task_id = task_id
        self.displayed_lines = 0
        self.collapsible_states = {}

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

    def action_view_code(self):
        self.app.push_screen(CodeViewScreen(self.task_id))

    def action_export_log(self):
        task = task_manager.get_task(self.task_id)
        if not task: return
        
        export_dir = Path("exports")
        export_dir.mkdir(exist_ok=True)
        log_file = export_dir / f"task_{self.task_id}_log.txt"
        
        with open(log_file, "w") as f:
            f.write(f"Goal: {task.get('original_goal', task['goal'])}\n\n")
            f.write("\n".join(task['history']))
        
        self.sub_title = f"Log exported to {log_file}"

    def action_export_all(self):
        self.action_export_log()
        
        export_dir = Path("exports") / f"task_{self.task_id}_files"
        workspace_path = workspace_manager.get_task_workspace(self.task_id)
        
        if export_dir.exists():
            shutil.rmtree(export_dir)
        
        if workspace_path.exists():
            shutil.copytree(workspace_path, export_dir)
            self.sub_title = f"Log and files exported to {export_dir.parent}"
        else:
            self.sub_title = "Log exported, but no workspace files to copy."

    def update_log(self) -> None:
        container = self.query_one("#task_log_container")
        task = task_manager.get_task(self.task_id)
        if not task: return

        self.collapsible_states = {
            c.id: c.collapsed for c in container.query(Collapsible) if c.id
        }

        redirect_input = self.query_one("#redirect_input_field", Input)
        user_input = self.query_one("#user_input_field", Input)
        user_input.styles.display = "block" if task['status'] == 'pending_input' else "none"
        redirect_input.styles.display = "block" if not redirect_input.disabled else "none"
        if task['status'] == 'pending_input' and user_input.disabled:
            user_input.disabled = False
            user_input.focus()

        if len(task['history']) == self.displayed_lines: return
        container.remove_children()
        
        container.mount(
            Static(Panel(task.get('original_goal', task['goal']), title="Original Goal", border_style="white"))
        )

        structured_history = parse_history_to_steps(task['history'])
        for i, step in enumerate(structured_history):
            children = []
            step_type = step.get("type")

            if step_type == "system":
                children.append(Static(Panel(escape(step['content']), title="System Message", border_style="blue")))
            elif step_type == "agent":
                thought_id = f"step_{i}_thought"
                action_id = f"step_{i}_action"

                if step.get("thought"):
                    is_collapsed = self.collapsible_states.get(thought_id, False)
                    thought_collapsible = Collapsible(
                        Markdown(f"{step['thought']}"), 
                        title="View Thought", 
                        id=thought_id,
                        collapsed=is_collapsed
                    )
                    children.append(thought_collapsible)
                
                if step.get("tool_call") or step.get("tool_result"):
                    console_content = []
                    if step.get("tool_call"):
                        display_call = dict(step["tool_call"])
                        if 'args' in display_call and 'content' in display_call['args']:
                            content = display_call['args']['content']
                            if content and len(content) > 200:
                                display_call['args']['content'] = content[:200] + "..."
                        
                        tool_call_str = json.dumps(display_call, indent=2)
                        console_content.append(Text.from_markup(f"[bold cyan]$> Tool Call:[/bold cyan]\n{tool_call_str}"))

                    if step.get("tool_result"):
                        escaped_result = escape(str(step['tool_result']))
                        console_content.append(Text.from_markup(f"\n[bold green]$> Tool Result:[/bold green]\n{escaped_result}"))
                    
                    if step.get("diff"):
                        console_content.append(Text.from_markup("\n[bold yellow]File Changes:[/bold yellow]\n"))
                        console_content.append(Syntax(step["diff"], "diff", theme="monokai", word_wrap=True))

                    is_collapsed = self.collapsible_states.get(action_id, True)
                    children.append(
                        Collapsible(Static(Text.assemble(*console_content)), title="View Action & Result", id=action_id, collapsed=is_collapsed)
                    )

            step_container = Vertical(*children)
            step_container.styles.border = ("round", Color.parse("grey"))
            step_container.styles.margin = (1, 0)
            step_container.styles.height = "auto"
            step_container.border_title = f"Step {i + 1}"
            container.mount(step_container)

        self.displayed_lines = len(task['history'])
        container.scroll_end(animate=False)
