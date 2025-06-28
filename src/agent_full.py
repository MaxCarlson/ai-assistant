import time
from abc import ABC, abstractmethod
from settings import MAX_TOKENS
from token_manager import TokenManager

class BaseAgent(ABC):
    @abstractmethod
    def handle_task(self, user_input: str, conversation_history: list) -> str:
        pass

class GeminiOnlyAgent(BaseAgent):
    def __init__(self, llm):
        self.llm = llm
        self.token_manager = TokenManager()
        self.request_count = 0
        self.start_time = time.time()

    def _rate_limited(self):
        now = time.time()
        if now - self.start_time > 60:
            self.request_count = 0
            self.start_time = now
        return self.request_count >= 60

    def handle_task(self, user_input, conversation_history):
        if self._rate_limited():
            return "[Rate Limit] Too many requests. Wait 60s."
        messages = [{"role": "user", "content": user_input}]
        response = self.llm.invoke(messages)
        self.request_count += 1
        return response.content

class RAGAgent(BaseAgent):
    def __init__(self, rag_manager):
        self.rag = rag_manager
        self.token_manager = TokenManager()
        self.request_count = 0
        self.start_time = time.time()

    def _rate_limited(self):
        now = time.time()
        if now - self.start_time > 60:
            self.request_count = 0
            self.start_time = now
        return self.request_count >= 60

    def handle_task(self, user_input, conversation_history):
        if self._rate_limited():
            return "[Rate Limit] Too many requests. Wait 60s."

        context = self.rag.get_context(user_input, conversation_history)
        conversation_history, context = self.token_manager.limit_tokens(
            user_input, conversation_history, context,
            max_tokens=MAX_TOKENS, percent_context=0.35
        )

        system_message = (
            f"You are an AI assistant. Use the following context to help answer the user's query:\n{context}\n"
        )
        messages = [{"role": "system", "content": system_message}]
        for entry in conversation_history:
            messages.append({"role": entry["role"], "content": entry["content"]})
        messages.append({"role": "user", "content": user_input})

        response = self.rag.query_llm.invoke(messages)
        self.request_count += 1
        return response.content
