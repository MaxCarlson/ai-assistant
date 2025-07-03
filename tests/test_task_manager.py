import unittest
from unittest.mock import patch, mock_open
from src import task_manager

class TestTaskManager(unittest.TestCase):

    @patch('src.task_manager._save_tasks')
    @patch('src.task_manager._load_tasks')
    def test_create_task(self, mock_load_tasks, mock_save_tasks):
        mock_load_tasks.return_value = {}
        task_id = task_manager.create_task("test goal")
        self.assertEqual(task_id, "0")
        mock_save_tasks.assert_called_once()

    @patch('src.task_manager._load_tasks')
    def test_get_task(self, mock_load_tasks):
        mock_load_tasks.return_value = {"0": {"id": "0", "goal": "test goal"}}
        task = task_manager.get_task("0")
        self.assertEqual(task["goal"], "test goal")

if __name__ == '__main__':
    unittest.main()
