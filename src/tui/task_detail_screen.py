from textual.screen import Screen
from textual.widgets import Header, Footer, Log
from src import task_manager

class TaskDetailScreen(Screen):
    """A screen to display the detailed, live-updating history of a single task."""

    def __init__(self, task_id: str):
        super().__init__()
        self.task_id = task_id
        self.displayed_lines = 0  # Keep track of how many lines we've shown

    def compose(self):
        yield Header(f"Task Detail - ID: {self.task_id}")
        yield Log(id="task_log", highlight=True)
        yield Footer()

    def on_mount(self):
        """Load initial history and start a timer to poll for updates."""
        self.update_log()
        # Refresh the log every second
        self.set_interval(1, self.update_log)

    def update_log(self) -> None:
        """Fetches the latest task history and appends new lines to the log."""
        log = self.query_one(Log)
        task = task_manager.get_task(self.task_id)

        if not task or 'history' not in task:
            if self.displayed_lines == 0:
                log.write("Task not found or has no history yet...")
                self.displayed_lines = 1
            return

        current_history = task['history']
        num_new_lines = len(current_history) - self.displayed_lines

        if num_new_lines > 0:
            # Get only the lines we haven't displayed yet
            lines_to_add = current_history[self.displayed_lines:]
            log.write_lines(lines_to_add)
            self.displayed_lines = len(current_history)
