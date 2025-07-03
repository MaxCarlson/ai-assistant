import unittest
from unittest.mock import patch, MagicMock
from src.tool_manager import write_file, read_file, modify_file, python
from src import task_manager

class TestToolManager(unittest.TestCase):

    def setUp(self):
        self.task_id = task_manager.create_task("test task")

    @patch('src.tool_manager.workspace_manager.get_safe_path')
    def test_write_file(self, mock_get_safe_path):
        mock_path = MagicMock()
        mock_get_safe_path.return_value = mock_path
        
        with patch('builtins.open', unittest.mock.mock_open()) as mock_open:
            result = write_file(self.task_id, "test.txt", "hello")
            self.assertEqual(result, "Successfully wrote 5 characters to test.txt")
            mock_open.assert_called_once_with(mock_path, 'w', encoding='utf-8')
            mock_open().write.assert_called_once_with("hello")

    @patch('src.tool_manager.workspace_manager.get_safe_path')
    def test_read_file(self, mock_get_safe_path):
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_get_safe_path.return_value = mock_path
        
        with patch('builtins.open', unittest.mock.mock_open(read_data="hello")) as mock_open:
            result = read_file(self.task_id, "test.txt")
            self.assertEqual(result, "hello")
            mock_open.assert_called_once_with(mock_path, 'r', encoding='utf-8')

    @patch('src.tool_manager.workspace_manager.get_safe_path')
    def test_modify_file(self, mock_get_safe_path):
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_get_safe_path.return_value = mock_path
        
        with patch('builtins.open', unittest.mock.mock_open(read_data="hello world")) as mock_open:
            result = modify_file(self.task_id, "test.txt", "world", "python")
            self.assertEqual(result, "Successfully modified test.txt.")
            mock_open().write.assert_called_once_with("hello python")

    @patch('src.tool_manager.subprocess.run')
    def test_python(self, mock_run):
        mock_result = MagicMock()
        mock_result.stdout = "hello"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        result = python(self.task_id, "print('hello')")
        self.assertEqual(result, "STDOUT:\nhello\nSTDERR:\n")
        mock_run.assert_called_once()

if __name__ == '__main__':
    unittest.main()
