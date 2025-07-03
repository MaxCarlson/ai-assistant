from transformers import AutoTokenizer

class FullTokenManager:
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
        """Limit tokens for conversation history and context, removing oldest history first."""
        user_input_tokens = self.count_tokens(user_input)
        context_limit = int(max_tokens * percent_context)
        
        # Trim context if it exceeds its cap
        if self.count_tokens(context) > context_limit:
            context = self.trim_to_token_limit(context, context_limit)
        
        context_tokens = self.count_tokens(context)
        
        # Calculate remaining tokens for history
        history_token_limit = max_tokens - user_input_tokens - context_tokens
        
        # Trim history if it exceeds its limit, removing from the beginning (oldest)
        history_tokens = sum(self.count_tokens(entry["content"]) for entry in conversation_history)
        
        if history_tokens > history_token_limit:
            trimmed_history = []
            current_tokens = 0
            # Iterate from newest to oldest, adding to new list until limit is reached
            for entry in reversed(conversation_history):
                entry_tokens = self.count_tokens(entry["content"])
                if current_tokens + entry_tokens <= history_token_limit:
                    trimmed_history.insert(0, entry)
                    current_tokens += entry_tokens
                else:
                    break # Stop when history is full
            conversation_history = trimmed_history

        return conversation_history, context
