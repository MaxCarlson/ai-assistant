import os
from enum import Enum
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from token_manager import TokenManager
from langchain.prompts import PromptTemplate
from langchain.schema import SystemMessage, HumanMessage
from typing import Callable

from langchain_google_genai import ChatGoogleGenerativeAI
from settings import MAX_TOKENS, EMBEDDINGS_PATH, EmbeddingModel, NOTES_SRC_PATH
from obsidian_embeddings import ObsidianEmbeddings

# Embedding Method Loader
def embeddingMethod(vector_store_name: str, embedding_model_name: str):
    # Define embedding methods
    def loadFAISSAllMiniLM():
        # Create vector store if it does not exist
        if not os.path.exists(f"{EMBEDDINGS_PATH}/{vector_store_name}"):
            ObsidianEmbeddings(notes_dir=NOTES_SRC_PATH).create_vector_store(vector_store_name)
        
        # Load embedding model and vector store
        embedding_model = HuggingFaceEmbeddings(model_name=embedding_model_name)
        return embedding_model, FAISS.load_local(
            vector_store_name, embedding_model, allow_dangerous_deserialization=True
        )
    
    # Switcher dictionary for embedding methods
    switcher = {
        "faiss_index": loadFAISSAllMiniLM,
        EmbeddingModel.ALL_MINILM_L6_V2: loadFAISSAllMiniLM,
        # Add additional methods here for other embedding types if necessary
    }
    
    # Retrieve the embedding method based on the enum
    #embedding_type = EmbeddingModel(vector_store_name)  # Converts the string to an enum if valid
    embedding_loader: Callable = switcher.get(vector_store_name)

    if embedding_loader is None:
        raise ValueError(f"Embedding type '{vector_store_name}' not supported or invalid.")

    return embedding_loader()  # Execute the appropriate method


class RAGManager:
    def __init__(self, query_model_name: str = "gemini-1.5-flash", 
                 embedding_model_name: str = "all-MiniLM-L6-v2",
                 notes_vector_store_name: str = "faiss_index"):
        
        self.query_model_name = query_model_name
        self.embedding_model_name = embedding_model_name
        self.notes_vector_store_name = notes_vector_store_name
        
        # Initialize embedding model and vector store
        #self.embedding_model = HuggingFaceEmbeddings(model_name=self.embedding_model_name)
        #self.vector_store = FAISS.load_local(
        #    self.notes_vector_store_name, self.embedding_model, allow_dangerous_deserialization=True
        #)
        self.embedding_model, self.vector_store = embeddingMethod(self.notes_vector_store_name, self.embedding_model_name)

        # Initialize text splitter for handling long queries
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500, chunk_overlap=50
        )

        # Token manager for trimming or splitting queries
        self.token_manager = TokenManager()

        # LLM for query generation
        self.query_llm = ChatGoogleGenerativeAI(model=self.query_model_name)

        # Prompt for query generation
        self.query_prompt = PromptTemplate(
            input_variables=["conversation", "user_input"],
            template=(
                "Given the following conversation history:\n"
                "{conversation}\n\n"
                "And the user's input:\n"
                "{user_input}\n\n"
                "Generate one or more concise queries to retrieve relevant documents."
            ),
        )

    def generate_queries(self, user_input: str, conversation_history: list) -> list:
        """Generate queries using the conversation history and user input."""
        # Format the conversation history
        conversation = "\n".join(
            [
                f"{entry['role']}: {entry['content']}"
                for entry in conversation_history[-5:]
            ]
        )

        # Build the system message content
        query_system_template = (
            "You are an AI assistant. Based on the following conversation history and user input, "
            "generate one or more concise queries to retrieve relevant documents:\n\n"
            "{conversation}\n\n"
            "User Input: {user_input}\n\n"
            "Queries:"
        )
        system_message_content = query_system_template.format(
            conversation=conversation, user_input=user_input
        )

        # Construct the messages
        messages = [
            SystemMessage(content=system_message_content),
            HumanMessage(content=user_input),
        ]

        # Invoke the LLM
        response = self.query_llm.invoke(messages)

        # Split the response into queries
        return response.content.split("\n")

    def retrieve_context(self, query: str, k: int = 5) -> str:
        """Retrieve relevant context for a single query."""
        docs = self.vector_store.similarity_search(query, k=k)
        return "\n".join([doc.page_content for doc in docs])


    def get_context(self, user_input: str, conversation_history: list, k: int = 5) -> str:
        """Retrieve context using multiple queries if necessary."""
        # Generate queries
        queries = self.generate_queries(user_input, conversation_history)

        # Retrieve context for each query and combine
        all_docs = []
        for query in queries:
            all_docs.extend(
                self.vector_store.similarity_search(query, k=max(1, k // len(queries)))
            )

        # Combine retrieved documents
        combined_context = "\n".join([doc.page_content for doc in all_docs[:k]])

        # Trim to token limit before embedding
        max_token_limit = 1024  # Model limit
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=max_token_limit, chunk_overlap=100)
        trimmed_context = text_splitter.split_text(combined_context)[0]  # Take only the first chunk

        return self.token_manager.trim_to_token_limit(
            trimmed_context, max_tokens=int(MAX_TOKENS * 0.35)
        )

