import time

class GeminiOnlyAgent:
    def __init__(self, llm):
        self.llm = llm
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
