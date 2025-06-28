from pathlib import Path
import os
from textual.screen import Screen
from textual.widgets import Header, Footer, DirectoryTree, Static
from textual.containers import Horizontal, Container
from rich.syntax import Syntax
from src import workspace_manager

class CodeViewScreen(Screen):
    """A screen for viewing files within a task's workspace."""

    CSS = """
    #dir_tree {
        width: 30%;
        height: 100%;
        border-right: solid $primary;
    }
    #code_view {
        width: 70%;
        height: 100%;
        overflow-y: auto;
    }
    """

    def __init__(self, task_id: str):
        super().__init__()
        self.task_id = task_id
        self.workspace_path = workspace_manager.get_task_workspace(self.task_id)

    def compose(self):
        yield Header(f"Code Viewer - Task {self.task_id}")
        with Horizontal():
            if self.workspace_path.exists() and any(self.workspace_path.iterdir()):
                yield DirectoryTree(str(self.workspace_path), id="dir_tree")
            else:
                yield Static("[yellow]Workspace is empty or not found.[/yellow]", id="dir_tree")
            
            yield Static("Select a file to view its contents.", id="code_view")
        yield Footer()

    def on_mount(self):
        try:
            self.query_one(DirectoryTree).focus()
        except Exception:
            pass

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected):
        """Called when the user clicks a file in the directory tree."""
        code_view = self.query_one("#code_view", Static)
        try:
            code = event.path.read_text()
            syntax = Syntax(code, Path(event.path).suffix.lstrip("."), theme="monokai", line_numbers=True)
            code_view.update(syntax)
        except Exception as e:
            code_view.update(f"[red]Error reading file: {e}[/red]")
