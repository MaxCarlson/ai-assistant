from abc import ABC, abstractmethod

class BaseAgent(ABC):
    """Abstract base class for all agents."""
    
    @abstractmethod
    def handle_task(self, user_input: str, conversation_history: list) -> str:
        """
        Process the user's input and return the assistant's response.

        :param user_input: The latest input from the user.
        :param conversation_history: A list of dictionaries representing the conversation so far.
                                     e.g., [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
        :return: A string containing the assistant's response.
        """
        pass
