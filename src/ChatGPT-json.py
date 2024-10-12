import json
from typing import List, Dict


def separate_conversations(filepath: str) -> List[Dict]:
    """
    Loads a conversations.json file from ChatGPT history and separates it into individual conversations.

    Args:
    filepath: The path to the conversations.json file.

    Returns:
    A list of dictionaries, where each dictionary represents a single conversation.
    """

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    conversations = []
    for conversation_data in data:
        conversation = {
            'title': conversation_data['title'],
            'create_time': conversation_data['create_time'],
            'update_time': conversation_data['update_time'],
            'messages': []
        }
        for message_id, message_info in conversation_data['mapping'].items():
            if message_info['message']:
                message = message_info['message']
                content_type = message['content']['content_type']

                if content_type == 'text':
                    content = ''.join(message['content']['parts'])
                elif content_type == 'code':
                    content = message['content']['text']
                elif content_type == 'tether_browsing_display':
                    content = message['content']['result']
                elif content_type == 'image_asset_pointer':
                    content = message['content']['parts'][0]
                else:
                    content = ''
                if len(content) > 0:
                    conversation['messages'].append({
                        'id': message['id'],
                        'author': message['author']['role'],
                        'content': content,
                        'create_time': message.get('create_time'),
                        'metadata': message['metadata']
                    })
        conversations.append(conversation)

    return conversations

# Example usage:
filepath = 'data/ChatGPT-2024-10-12-10-05-59/conversations.json'
conversations = separate_conversations(filepath)

# Now you can access individual conversations and their messages
for conversation in conversations:
    print(f"Conversation Title: {conversation['title']}")
    for message in conversation['messages']:
        print(f"  {message['author']}: {message['content']}")