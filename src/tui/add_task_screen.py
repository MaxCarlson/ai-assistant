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
            yield Input(value=".", placeholder="Workspace Path (e.g., . for this repo)", id="workspace_path_input")
            yield Checkbox("Create New Git Branch for this Task", value=True, id="create_branch_checkbox")
            
            yield Label("\nOptional Tools", classes="group-title")
            with VerticalScroll(id="tools_container"):
                optional_tools = [t for t in tool_manager.TOOLS.keys() if t not in task_manager.CORE_TOOLS]
                for tool_name in optional_tools:
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
            
            workspace_path = self.query_one("#workspace_path_input", Input).value or "."
            create_branch = self.query_one("#create_branch_checkbox", Checkbox).value

            allowed_tools = [
                cb.label.plain for cb in self.query(Checkbox) if cb.value
            ]
            
            task_id = task_manager.create_task(
                goal=goal,
                allowed_tools=allowed_tools,
                workspace_path=workspace_path,
                create_branch=create_branch
            )
            self.dismiss(task_id)
        else:
            self.dismiss(None)
