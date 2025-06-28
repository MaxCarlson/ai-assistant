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
            yield Input(value="15", placeholder="Max steps...", id="steps_input")
            
            yield Label("\nContext & Permissions", classes="group-title")
            yield Input(placeholder="Context paths (e.g., src/, README.md)", id="context_paths_input")
            yield Input(placeholder="Read-only paths (e.g., src/utils/)", id="read_only_paths_input")

            yield Label("\nAllowed Tools", classes="group-title")
            with VerticalScroll(id="tools_container"):
                # Filter out core tools which are always available
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
            
            max_steps_str = self.query_one("#steps_input", Input).value
            max_steps = int(max_steps_str) if max_steps_str.isdigit() else 15
            
            context_paths_str = self.query_one("#context_paths_input", Input).value
            context_paths = [p.strip() for p in context_paths_str.split(',') if p.strip()]

            read_only_paths_str = self.query_one("#read_only_paths_input", Input).value
            read_only_paths = [p.strip() for p in read_only_paths_str.split(',') if p.strip()]

            allowed_tools = [
                cb.label.plain for cb in self.query(Checkbox) if cb.value
            ]
            
            task_id = task_manager.create_task(
                goal=goal,
                max_steps=max_steps,
                allowed_tools=allowed_tools,
                context_paths=context_paths,
                read_only_paths=read_only_paths
            )
            self.dismiss(task_id)
        else:
            self.dismiss(None)
