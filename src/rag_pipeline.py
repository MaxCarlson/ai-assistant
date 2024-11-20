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
                f"You are an AI assistant with knowledge of my past projects and notes.\n"
                f"Context:\n{context}\n\n"
                f"Question: {query_text}\n\n"
                f"Please provide a clear and concise answer based on the context above."
            )

        # Step 3: Generate a response using the LLM
        response = self.llm_manager.generate(prompt)

        # Truncate long responses
        max_response_length = 2000
        if len(response) > max_response_length:
            response = response[:max_response_length] + "\n[Response truncated.]"
        return response



