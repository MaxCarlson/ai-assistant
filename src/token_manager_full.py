from transformers import AutoTokenizer

class TokenManager:
    def __init__(self):
        # Initialize the tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained("gpt2")
    
    def count_tokens(self, text: str) -> int:
        """Estimate token count using Hugging Face tokenizer."""
        return len(self.tokenizer.encode(text, truncation=False))
    
    def trim_to_token_limit(self, text: str, max_tokens: int) -> str:
        """Trim text to fit within the max token limit."""
        tokens = self.tokenizer.encode(text, truncation=False)
        if len(tokens) > max_tokens:
            return self.tokenizer.decode(tokens[:max_tokens])
        return text

    def limit_tokens(self, user_input: str, conversation_history: list, context: str, max_tokens: int, percent_context: float) -> tuple:
        """Limit tokens for conversation history and context."""
        user_input_tokens = self.count_tokens(user_input)
        context_limit = int(max_tokens * percent_context)
        available_tokens = max_tokens - user_input_tokens

        # Estimate tokens for conversation history and context
        history_tokens = sum(self.count_tokens(entry["content"]) for entry in conversation_history)
        context_tokens = self.count_tokens(context)

        # Trim context if it exceeds its cap
        if context_tokens > context_limit:
            context = self.trim_to_token_limit(context, context_limit)

        # Trim conversation history if combined exceeds available tokens
        if history_tokens + context_tokens > available_tokens:
            excess_tokens = history_tokens + context_tokens - available_tokens
            trimmed_history = []
            for entry in reversed(conversation_history):
                tokens = self.count_tokens(entry["content"])
                if tokens <= excess_tokens:
                    excess_tokens -= tokens
                else:
                    trimmed_history.insert(0, entry)
            conversation_history = trimmed_history

        return conversation_history, context
