from textual.screen import ModalScreen
from textual.widgets import Input, Button, Label, Checkbox
from textual.containers import Vertical, VerticalScroll
from src import task_manager, tool_manager

class AddTaskScreen(ModalScreen):
    """A modal screen for creating a new task."""

    def compose(self):
        with Vertical(id="add_task_dialog"):
            yield Label("Create New Task", id="add_task_title")
            yield Input(placeholder="Enter task goal...", id="goal_input")
            yield Input(placeholder="Working Directory (optional, defaults to ./workspaces)", id="work_dir_input")
            yield Input(value="15", placeholder="Max steps...", id="steps_input")
            yield Label("Allowed Tools:")
            with VerticalScroll(id="tools_container"):
                for tool_name in tool_manager.TOOLS.keys():
                    yield Checkbox(tool_name, value=True, id=f"cb_{tool_name}")
            
            with Vertical(id="add_task_buttons"):
                yield Button("Create", variant="primary", id="create_button")
                yield Button("Cancel", id="cancel_button")

    def on_button_pressed(self, event: Button.Pressed):
        """Handle create or cancel button presses."""
        if event.button.id == "create_button":
            goal = self.query_one("#goal_input", Input).value
            if not goal:
                return
            
            work_dir = self.query_one("#work_dir_input", Input).value or None
            max_steps_str = self.query_one("#steps_input", Input).value
            max_steps = int(max_steps_str) if max_steps_str.isdigit() else 15
            
            allowed_tools = [
                cb.label.plain for cb in self.query(Checkbox) if cb.value
            ]
            
            task_id = task_manager.create_task(
                goal=goal,
                max_steps=max_steps,
                allowed_tools=allowed_tools,
                working_dir=work_dir
            )
            self.dismiss(task_id)
        else:
            self.dismiss(None)
