import pytest
import base64
import json
from src import tool_manager
from src import workspace_manager

def test_write_file(tmp_path):
    """Tests that the write_file tool correctly decodes and writes content."""
    workspace_manager.BASE_WORKSPACE_DIR = tmp_path
    task_id = "test_task_0"
    file_path = "test_file.txt"
    content = "Hello, World!"
    content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')

    result = tool_manager.write_file(task_id, file_path, content_b64)
    
    assert "Successfully wrote" in result
    
    written_file = tmp_path / task_id / file_path
    assert written_file.exists()
    assert written_file.read_text() == content

def test_execute_python_code(tmp_path):
    """Tests that the execute_python_code tool runs a script and captures output."""
    workspace_manager.BASE_WORKSPACE_DIR = tmp_path
    task_id = "test_task_1"
    file_path = "test_script.py"
    content = "print('Execution successful!')"
    content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    
    # First, write the file to be executed
    tool_manager.write_file(task_id, file_path, content_b64)

    result = tool_manager.execute_python_code(task_id, file_path)
    
    assert "STDOUT" in result
    assert "Execution successful!" in result
    assert "STDERR" in result

def test_web_search(mocker):
    """Tests that the web_search tool correctly parses mocked HTML responses."""
    # Mock the requests.post call to avoid actual network requests
    mock_response = mocker.Mock()
    mock_response.text = """
    <a class="result__a" href="https://example.com/1"><b>Title 1</b></a>
    <a class="result__snippet">Snippet 1...</a>
    <a class="result__a" href="https://example.com/2">Title 2</a>
    <a class="result__snippet"><b>Snippet 2...</b></a>
    """
    mocker.patch('requests.post', return_value=mock_response)

    result_str = tool_manager.web_search("any query")
    result_data = json.loads(result_str)

    assert len(result_data) == 2
    assert result_data[0]["title"] == "Title 1"
    assert result_data[0]["href"] == "https://example.com/1"
    assert result_data[0]["body"] == "Snippet 1..."
    assert result_data[1]["title"] == "Title 2"
