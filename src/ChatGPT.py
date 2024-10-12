import json

# Load the JSON file
with open('data/ChatGPT-2024-10-12-10-05-59/conversations.json', 'r') as f:
    chat_history = json.load(f)

def find_root_node(mapping):
    """Find the root node in the mapping."""
    for node_id, node_data in mapping.items():
        if node_data.get("parent") is None:  # Root node has no parent
            return node_id
    return None  # In case no root is found

# Function to recursively traverse the "mapping" structure
def traverse_mapping(mapping, node_id, conversation=[]):
    node = mapping.get(node_id)
    if not node or not node.get("message"):  # If no message exists
        return conversation

    skip = False

    # Initialize message_content with a default value
    message_content = ""

    # Check if the 'parts' field exists, if not handle it differently
    content = node['message'].get('content', {})
    if 'parts' in content:
        message_content = content['parts'][0]
    elif 'result' in content:
        # Handle query returns
        message_content = content.get('result', "Unknown query format")        
    else:
        # Handle special cases where 'parts' is missing
        message_content = content.get('text', "Unknown content format")
        if 'mclick' in message_content[0:6]:
            skip = True
    
    role = node['message']['author']['role']
    
    if len(message_content) == 0:
        a = 5

    # Append this message to the conversation
    if not skip and not role in 'tool' and len(message_content) > 0:
        conversation.append(f"{role}: {message_content}")

    # Continue traversing child nodes
    for child_id in node.get("children", []):
        conversation = traverse_mapping(mapping, child_id, conversation)
    
    return conversation


# Extract conversations from each chat session
conversations = []

for chat in chat_history:
    root_id = find_root_node(chat['mapping'])  # Find the actual root node
    if root_id:
        conversation = traverse_mapping(chat['mapping'], root_id)
        conversations.append("\n".join(conversation))

# Print an example conversation
print(conversations[0])

