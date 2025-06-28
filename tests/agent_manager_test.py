import pytest
from src.agent_manager import _extract_json_from_response
import json

# Test cases simulating various faulty AI responses.
# These are constructed by joining lists of strings to avoid triple-quote issues.

# 1. Standard response with markdown fences
case_1 = "\n".join([
    "```json",
    "{",
    '    "thought": "This is a standard response.",',
    '    "tool_call": "some_tool"',
    "}",
    "```"
])

# 2. Response with leading newlines and whitespace before the fence
case_2 = "\n".join([
    "",
    "  ```json",
    "{",
    '    "thought": "Response with leading whitespace.",',
    '    "tool_call": "some_tool"',
    "}",
    "```"
])

# 3. Response with no markdown fence, just the JSON object
case_3 = "\n".join([
    "{",
    '    "thought": "Response with no markdown fence.",',
    '    "tool_call": "some_tool"',
    "}"
])

# 4. Response with text before and after the JSON fence
case_4 = "\n".join([
    "Here is the JSON you requested:",
    "```json",
    "{",
    '    "thought": "Response with surrounding text.",',
    '    "tool_call": "some_tool"',
    "}",
    "```",
    "I hope this helps!"
])

# 5. The exact failure case: leading newline inside the fence
case_5 = "\n".join([
    "```json",
    "",
    "{",
    '    "thought": "The exact failure case.",',
    '    "tool_call": "some_tool"',
    "}",
    "```"
])

@pytest.mark.parametrize("response_text, expected_thought", [
    (case_1, "This is a standard response."),
    (case_2, "Response with leading whitespace."),
    (case_3, "Response with no markdown fence."),
    (case_4, "Response with surrounding text."),
    (case_5, "The exact failure case."),
])
def test_extract_json_from_response(response_text, expected_thought):
    """
    Tests that the JSON extraction function can handle various malformed inputs.
    """
    json_str = _extract_json_from_response(response_text)
    
    # Assert that a string was actually extracted
    assert json_str is not None, f"Failed to extract JSON from: {response_text}"
    
    # Try to parse the extracted string
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        pytest.fail(f"Extracted string is not valid JSON: {repr(json_str)}")

    # Assert the content is correct
    assert data.get("thought") == expected_thought
