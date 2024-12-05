import os
from enum import Enum
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from token_manager import TokenManager
from langchain.prompts import PromptTemplate
from langchain.schema import SystemMessage, HumanMessage

from langchain_google_genai import ChatGoogleGenerativeAI
from settings import MAX_TOKENS, EMBEDDINGS_PATH, EmbeddingType
from obsidian_embeddings import ObsidianEmbeddings

def embeddingMethod(vector_store_name: str, embedding_model_name: str):
    def loadFAISSAllMiniLM():
        if not os.path.exists(f"{EMBEDDINGS_PATH}/{vector_store_name}"):
            ObsidianEmbeddings(notes_dir=EMBEDDINGS_PATH).create_vector_store(vector_store_name)
          
        embedding_model = HuggingFaceEmbeddings(model_name=embedding_model_name)
        return embedding_model, FAISS.load_local(
            vector_store_name, embedding_model, allow_dangerous_deserialization=True
        )
    
    switcher = {
        Enum('ALL_MINILM_L6_V2') : 
        
        
            
    }

    return switcher.get(vector_store_name, "Saved Embedding Not Found")()

class RAGManager:
    def __init__(self, query_model_name: str = "gemini-1.5-flash", 
                 embedding_model_name: str = "all-MiniLM-L6-v2",
                 vector_store_name: str = "faiss_index"):
        
        self.query_model_name = query_model_name
        self.embedding_model_name = embedding_model_name
        self.vector_store_name = vector_store_name
        
        # Initialize embedding model and vector store
        #self.embedding_model = HuggingFaceEmbeddings(model_name=self.embedding_model_name)
        #self.vector_store = FAISS.load_local(
        #    self.vector_store_name, self.embedding_model, allow_dangerous_deserialization=True
        #)
        self.embedding_model, self.vector_store = embeddingMethod(self.vector_store_name, self.embedding_model_name)

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

    def get_context(
        self, user_input: str, conversation_history: list, k: int = 5
    ) -> str:
        """Retrieve context using multiple queries if necessary."""
        # Generate queries
        queries = self.generate_queries(user_input, conversation_history)

        # TODO: There are many queries returned where multiple lines aren't techinally blank,
        # but are blank for all intents and purposes. We should filter these out when they occur.

        # Retrieve context for each query and combine
        all_docs = []
        for query in queries:
            all_docs.extend(
                self.vector_store.similarity_search(query, k=max(1, k // len(queries)))
            )

        # Combine and limit the retrieved context
        combined_context = "\n".join([doc.page_content for doc in all_docs[:k]])
        return self.token_manager.trim_to_token_limit(
            combined_context, max_tokens=int(MAX_TOKENS * 0.35)
        )
