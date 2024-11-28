class RAGPipeline:
    """
    A class to handle the Retrieval-Augmented Generation (RAG) pipeline.
    """

    def __init__(self, embedding_manager, llm_manager, top_k=5):
        """
        Initialize the RAG pipeline.

        :param embedding_manager: Instance of EmbeddingManager.
        :param llm_manager: Instance of LLMManager.
        :param top_k: Number of top results to retrieve from the vector store.
        """
        self.embedding_manager = embedding_manager
        self.llm_manager = llm_manager
        self.top_k = top_k
        
    def trim_input(context, query, max_tokens=2048, reserve_tokens=256):
        """
        Trims context to fit within the model's token limit.

        :param context: Retrieved context string.
        :param query: User query string.
        :param max_tokens: Maximum token limit for the model.
        :param reserve_tokens: Tokens reserved for the query and response.
        :return: Trimmed context and query.
        """
        query_tokens = tokenizer.encode(query, add_special_tokens=False)
        context_tokens = tokenizer.encode(context, add_special_tokens=False)

        # Reserve space for the query and response
        available_tokens = max_tokens - reserve_tokens - len(query_tokens)

        # Trim the context if it exceeds available tokens
        if len(context_tokens) > available_tokens:
            context_tokens = context_tokens[:available_tokens]

        # Decode trimmed context
        trimmed_context = tokenizer.decode(context_tokens)
        return trimmed_context, query

    def query(self, query_text):
        """
        Process a user query through the RAG pipeline.

        :param query_text: User's input query string.
        :return: Generated response from the LLM.
        """
        # Step 1: Retrieve relevant chunks
        retrieved_docs = self.embedding_manager.query(query_text, top_k=self.top_k)
        
        # Fallback if no context is retrieved
        if not retrieved_docs:
            context = (
                "No relevant context was found in your notes. Please provide more details or clarify your query. "
                "For example, mention a specific project, topic, or time period to help me assist you better."
            )
            no_context = True
        else:
            context = "\n".join([doc["content"] for doc in retrieved_docs])
            no_context = False

        # Step 2: Create a prompt
        if no_context:
            prompt = (
                f"You are an AI assistant that helps users with their notes and projects.\n\n"
                f"The user asked: '{query_text}'. However, no relevant context was found in their notes.\n\n"
                f"Please provide a helpful answer based on general knowledge or suggest how the user can refine their question "
                f"to get more specific results."
            )
        else:
            prompt = (
                f"You are an AI assistant helping with knowledge retrieval and synthesis.\n\n"
                f"Context (retrieved from my notes):\n{context}\n\n"
                f"Based on the above context, answer the following question concisely and clearly:\n"
                f"{query_text}\n\n"
                f"Provide a short, synthesized answer. Do not simply repeat the context."
            )


        # Step 3: Generate a response using the LLM
        response = self.llm_manager.generate(prompt)

        # Truncate long responses
        max_response_length = 10000
        if len(response) > max_response_length:
            response = response[:max_response_length] + "\n[Response truncated.]"
        return response



