import enum

MAX_TOKENS = 4096  # Total token limit for the model
MAX_OUTPUT_TOKENS = 512  # Maximum tokens for the response
EMBEDDINGS_PATH = "data/embeddings"  # Path to the FAISS index
NOTES_EMBEDDING_PATH = EMBEDDINGS_PATH + "/notes"  # Path to the notes embeddings
CODE_EMBEDDING_PATH = EMBEDDINGS_PATH + "/code"  # Path to the code embeddings
MEMORY_EMBEDDING_PATH = EMBEDDINGS_PATH + "/memory"  # Path to the memory embeddings

class EmbeddingType(enum.Enum):
    """Enumeration of supported embedding types."""
    ALL_MINILM_L6_V2 = "all-MiniLM-L6-v2" # Hugging Face embedding model name - lightweight
    TEXT_EMBEDDING_005 = "text-embedding-005" # Google Vertex AI - Google's Top Embedding Model