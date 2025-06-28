from src.base_agent import BaseAgent
from src.settings import MAX_TOKENS
from src.rag_manager import RAGManager
from src.token_manager_full import FullTokenManager

class RAGAgent(BaseAgent):
    """
    An advanced agent that uses a RAG manager to retrieve context before
    querying the LLM. Requires full dependencies.
    """
    def __init__(self, query_model_name: str = "gemini-1.5-pro", embedding_model_name: str = "all-MiniLM-L6-v2"):
        self.rag_manager = RAGManager(query_model_name, embedding_model_name)
        self.token_manager = FullTokenManager()

    def handle_task(self, user_input: str, conversation_history: list) -> str:
        """
        Handles a task by first retrieving context, then limiting tokens,
        and finally invoking the LLM with the context.
        """
        context = self.rag_manager.get_context(user_input, conversation_history)

        limited_history, limited_context = self.token_manager.limit_tokens(
            user_input=user_input,
            conversation_history=conversation_history,
            context=context,
            max_tokens=MAX_TOKENS,
            percent_context=0.35
        )

        system_message = (
            "You are an AI assistant. Use the following context to help answer the user's query:\n"
            f"--- CONTEXT ---\n{limited_context}\n--- END CONTEXT ---"
        )
        messages = [{"role": "system", "content": system_message}]
        for entry in limited_history:
            messages.append({"role": entry["role"], "content": entry["content"]})
        messages.append({"role": "user", "content": user_input})

        try:
            response = self.rag_manager.query_llm.invoke(messages)
            return response.content
        except Exception as e:
            return f"[Error] Failed to get response from API: {e}"
