from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, DataTable, Log
from textual.binding import Binding
from src import task_manager

# Fixed: This should be a Screen that CONTAINS a DataTable
class TaskListScreen(Screen):
    """A screen to display the list of all tasks."""
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="task_table")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("ID", "Status", "Goal")
        self.update_tasks(table)

    def update_tasks(self, table: DataTable):
        table.clear()
        tasks = task_manager.get_all_tasks()
        if not tasks or tasks[0]['id'] == 'ERR':
            table.add_row("N/A", "N/A", "No tasks created yet.")
        else:
            for task in tasks:
                goal = task.get('goal', 'N/A')
                display_goal = (goal[:70] + '...') if len(goal) > 73 else goal
                table.add_row(str(task['id']), task['status'], display_goal)

    def on_data_table_row_selected(self, event):
        # We get the task ID from the first column of the selected row
        task_id = event.data_table.get_cell_at(event.cursor_coordinate)
        self.app.push_screen(TaskDetailScreen(task_id))

# Fixed: This should be a Screen that CONTAINS a Log
class TaskDetailScreen(Screen):
    """A screen to display the detailed history of a single task."""
    def __init__(self, task_id: str) -> None:
        super().__init__()
        self.task_id = task_id

    def compose(self) -> ComposeResult:
        yield Header()
        yield Log(id="task_log")
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one(Log)
        self.border_title = f"Task Detail - ID: {self.task_id}"
        task = task_manager.get_task(self.task_id)
        if task and 'history' in task:
            log.write_lines(task['history'])
        else:
            log.write(f"Error: Task {self.task_id} not found or has no history.")

class TUI(App):
    """The main Textual User Interface application."""
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("escape", "app.pop_screen", "Back"),
    ]

    def on_mount(self) -> None:
        self.push_screen(TaskListScreen())
