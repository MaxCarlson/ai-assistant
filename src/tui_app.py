from textual.app import App
from textual.binding import Binding
from src.tui.task_list_screen import TaskListScreen

class TUI(App):
    """The main Textual User Interface application."""

    BINDINGS = [
        Binding("q", "quit", "Quit TUI"),
        Binding("escape", "app.pop_screen", "Back"),
    ]
    
    def __init__(self, agent_manager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agent_manager = agent_manager

    def on_mount(self):
        """Push the initial screen when the app starts."""
        self.push_screen(TaskListScreen(agent_manager=self.agent_manager))
