class TokenManager:
    def count_tokens(self, text: str) -> int:
        # Rough estimate: 1 token ≈ 0.75 words
        return int(len(text.split()) / 0.75)

    def trim_to_token_limit(self, text: str, max_tokens: int) -> str:
        words = text.split()
        if len(words) > max_tokens:
            return " ".join(words[:max_tokens])
        return text

    def limit_tokens(self, user_input, conversation_history, context, max_tokens, percent_context):
        # Simple pass-through for minimal mode.
        return conversation_history, context
