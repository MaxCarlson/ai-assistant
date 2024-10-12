import json
from typing import List, Dict


class ChatGPTConversations:
    """
    A class to load and manage ChatGPT conversation history from a JSON file.
    """

    def __init__(self, filepath: str):
        """
        Initializes the ChatGPTConversations class by loading the conversation data from the provided filepath.

        Args:
        filepath: The path to the conversations.json file.
        """
        self.filepath = filepath
        self.conversations = self._load_conversations()

    def _load_conversations(self) -> List[Dict]:
        """
        Loads and parses the conversations from the JSON file.

        Returns:
        A list of dictionaries where each dictionary represents a single conversation.
        """
        with open(self.filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        conversations = []
        for conversation_data in data:
            conversation = {
                'title': conversation_data['title'],
                'create_time': conversation_data['create_time'],
                'update_time': conversation_data['update_time'],
                'messages': self._extract_messages(conversation_data)
            }
            conversations.append(conversation)

        return conversations

    def _extract_messages(self, conversation_data: Dict) -> List[Dict]:
        """
        Extracts messages from a single conversation.

        Args:
        conversation_data: A dictionary containing conversation data.

        Returns:
        A list of message dictionaries.
        """
        messages = []
        for message_id, message_info in conversation_data['mapping'].items():
            if message_info['message']:
                message = message_info['message']
                content_type = message['content']['content_type']
                content = self._extract_content(content_type, message)

                if len(content) > 0:
                    messages.append({
                        'id': message['id'],
                        'author': message['author']['role'],
                        'content': content,
                        'create_time': message.get('create_time'),
                        'metadata': message['metadata']
                    })
        return messages

    def _extract_content(self, content_type: str, message: Dict) -> str:
        """
        Extracts the content of a message based on its type.

        Args:
        content_type: The type of content ('text', 'code', 'tether_browsing_display', etc.).
        message: A dictionary containing the message data.

        Returns:
        A string containing the message content.
        """
        content = ''
        if content_type == 'text':
            content = ''.join(message['content']['parts'])
        elif content_type == 'code':
            content = message['content']['text']
        elif content_type == 'tether_browsing_display':
            content = message['content']['result']
        elif content_type == 'image_asset_pointer':
            content = message['content']['parts'][0]
        return content

    def get_conversations(self) -> List[Dict]:
        """
        Returns the list of loaded conversations.

        Returns:
        A list of dictionaries representing the conversations.
        """
        return self.conversations

    def print_conversation_summary(self) -> None:
        """
        Prints a summary of all conversations and their messages.
        """
        for conversation in self.conversations:
            print(f"Conversation Title: {conversation['title']}")
            for message in conversation['messages']:
                print(f"  {message['author']}: {message['content']}")

if __name__ == '__main__':
    # Example usage:
    filepath = 'data/ChatGPT-2024-10-12-10-05-59/conversations.json'
    chatgpt_history = ChatGPTConversations(filepath)

    # Get conversations
    conversations = chatgpt_history.get_conversations()

    # Print a summary of conversations and messages
    chatgpt_history.print_conversation_summary()
