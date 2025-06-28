from textual.app import App
from textual.binding import Binding
from src.tui.task_list_screen import TaskListScreen

class TUI(App):
    """The main Textual User Interface application."""

    BINDINGS = [
        Binding("q", "quit", "Quit TUI"),
        Binding("escape", "app.pop_screen", "Back"),
    ]
    
    def on_mount(self):
        """Push the initial screen when the app starts."""
        self.push_screen(TaskListScreen())
