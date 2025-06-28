from textual.screen import Screen
from textual.widgets import Header, Footer, DataTable
from textual.binding import Binding
from src import task_manager
from .add_task_screen import AddTaskScreen
from .task_detail_screen import TaskDetailScreen

class TaskListScreen(Screen):
    """The main screen showing the list of all tasks, with live updates."""

    BINDINGS = [Binding("a", "add_task", "Add Task")]

    def compose(self):
        yield Header("Task List")
        yield DataTable(id="task_table", cursor_type="row")
        yield Footer()

    def on_mount(self):
        """Set up the table and a timer to refresh it periodically."""
        table = self.query_one(DataTable)
        table.add_columns("ID", "Status", "Goal")
        self.update_tasks()
        # Refresh the task list every 2 seconds
        self.set_interval(2, self.update_tasks)

    def update_tasks(self) -> None:
        """Clears and re-populates the task table with the latest data."""
        table = self.query_one(DataTable)
        
        # Store the current cursor position to restore it after refresh
        current_cursor_row = table.cursor_row
        
        table.clear()
        tasks = task_manager.get_all_tasks()
        if not tasks:
            table.add_row("N/A", "N/A", "No tasks yet. Press 'a' to add one.")
        else:
            for task in tasks:
                goal = task.get('goal', 'N/A')
                display_goal = (goal[:70] + '...') if len(goal) > 73 else goal
                table.add_row(str(task['id']), task['status'], display_goal, key=str(task['id']))
        
        # Restore the cursor if it's still valid
        if 0 <= current_cursor_row < len(table.rows):
            # Fixed: Use the correct 'move_cursor' method instead of direct assignment.
            table.move_cursor(row=current_cursor_row)

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        """Called when the user presses Enter on a task."""
        if event.row_key.value:
            self.app.push_screen(TaskDetailScreen(event.row_key.value))

    def action_add_task(self) -> None:
        """Called when the user presses 'a'."""
        def on_dismiss(created: bool):
            if created:
                self.update_tasks()
        
        self.app.push_screen(AddTaskScreen(), on_dismiss)
