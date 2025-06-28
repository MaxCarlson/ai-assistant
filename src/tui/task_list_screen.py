import threading
from textual.screen import Screen
from textual.widgets import Header, Footer, DataTable
from textual.binding import Binding
from src import task_manager, agent_manager
from .add_task_screen import AddTaskScreen
from .task_detail_screen import TaskDetailScreen

class TaskListScreen(Screen):
    """The main screen showing the list of all tasks, with live updates."""

    BINDINGS = [
        Binding("a", "add_task", "Add Task"),
        Binding("s", "start_resume_task", "Start / Resume"),
        Binding("c", "clone_task", "Clone Task"),
        Binding("d", "delete_task", "Delete Task"),
    ]

    def compose(self):
        yield Header("Task List")
        yield DataTable(id="task_table", cursor_type="row")
        yield Footer()

    def on_mount(self):
        """Set up the table and a timer to refresh it periodically."""
        table = self.query_one(DataTable)
        table.add_columns("ID", "Status", "Goal")
        self.update_tasks()
        self.set_interval(2, self.update_tasks)

    def _start_task_in_background(self, task_id: str):
        """Helper method to start an agent task in a new thread."""
        agent = agent_manager.AgentManager(debug=True)
        task_thread = threading.Thread(target=agent.start_task, args=(task_id,))
        task_thread.daemon = True
        task_thread.start()
        self.sub_title = f"Task {task_id} started/resumed in background"

    def update_tasks(self) -> None:
        """Clears and re-populates the task table with the latest data."""
        table = self.query_one(DataTable)
        cursor_row = table.cursor_row
        table.clear()
        tasks = task_manager.get_all_tasks()
        if not tasks:
            table.add_row("N/A", "N/A", "No tasks yet. Press 'a' to add one.")
        else:
            for task in tasks:
                goal = task.get('goal', 'N/A')
                display_goal = (goal[:70] + '...') if len(goal) > 73 else goal
                table.add_row(str(task['id']), task['status'], display_goal, key=str(task['id']))
        
        if 0 <= cursor_row < len(table.rows):
            table.move_cursor(row=cursor_row)

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        """Called when the user presses Enter on a task to view details."""
        if event.row_key.value:
            self.app.push_screen(TaskDetailScreen(event.row_key.value))

    def action_add_task(self) -> None:
        """Called when the user presses 'a' to add a new task."""
        def on_dismiss(task_id: str | None):
            if task_id:
                self.update_tasks()
                self._start_task_in_background(task_id)
        
        self.app.push_screen(AddTaskScreen(), on_dismiss)

    def _get_key_for_selected_row(self) -> str | None:
        """Safely gets the key for the currently selected row."""
        table = self.query_one(DataTable)
        if not table.row_count or table.cursor_row < 0:
            return None
        try:
            row_key = list(table.rows.keys())[table.cursor_row]
            return row_key.value
        except (IndexError, AttributeError):
            return None

    def action_start_resume_task(self) -> None:
        """Called when 's' is pressed. Starts or resumes a selected task."""
        task_id = self._get_key_for_selected_row()
        if not task_id:
            return
        
        task = task_manager.get_task(task_id)
        resumable_states = ['pending', 'in_progress', 'failed']
        if task and task['status'] in resumable_states:
            self._start_task_in_background(task['id'])
        elif task and task['status'] == 'completed_max_steps':
            task_manager.extend_task_steps(task_id)
            self._start_task_in_background(task_id)

    def action_clone_task(self) -> None:
        """Called when 'c' is pressed. Creates a new task from an existing one."""
        task_id = self._get_key_for_selected_row()
        if not task_id:
            return
        
        original_task = task_manager.get_task(task_id)
        if original_task:
            new_task_id = task_manager.create_task(
                # Fixed: Use the original_goal for cloning.
                goal=original_task.get('original_goal', original_task['goal']),
                max_steps=original_task['max_steps'],
                allowed_tools=original_task['allowed_tools'],
                working_dir=original_task.get('working_dir')
            )
            self.update_tasks()
            self._start_task_in_background(new_task_id)
            self.sub_title = f"Cloned task {task_id} to new task {new_task_id}"

    def action_delete_task(self) -> None:
        """Called when the user presses 'd' to delete a task."""
        task_id = self._get_key_for_selected_row()
        if not task_id:
            return
        
        task_manager.delete_task(task_id)
        self.update_tasks()
        self.sub_title = f"Task {task_id} deleted"
