import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_community.vectorstores import FAISS
from alive_progress import alive_bar
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_googlevertexai import GoogleVertexEmbeddings

class ObsidianEmbeddings:
    def __init__(self, notes_dir, chunk_size=1000, chunk_overlap=50):
        self.notes_dir = os.path.expanduser(notes_dir)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " "]
        )
        self.documents = []
        self.vector_store = None

    def set_embedding_model(self, model_type, **kwargs):
        """Set the embedding model dynamically."""
        if model_type == "huggingface":
            model_name = kwargs.get("model_name", "all-MiniLM-L6-v2")
            self.embedding_model = HuggingFaceEmbeddings(model_name=model_name)
        elif model_type == "google_vertex":
            model_name = kwargs.get("model_name", "text-embedding-ada-002")
            self.embedding_model = GoogleVertexEmbeddings(model_name=model_name)
        else:
            raise ValueError(f"Unsupported model type: {model_type}")

    def load_documents(self):
        """Load and split documents from the notes directory."""
        files = [f for f in os.listdir(self.notes_dir) if os.path.isfile(os.path.join(self.notes_dir, f))]
        print("Processing files...")
        with alive_bar(len(files)) as file_bar:
            for file_name in files:
                file_path = os.path.join(self.notes_dir, file_name)
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    chunks = self.text_splitter.split_text(content)
                    for chunk in chunks:
                        self.documents.append(Document(page_content=chunk))
                file_bar()
        print(f"Loaded {len(self.documents)} document chunks.")

    def create_vector_store(self, save_path="faiss_index"):
        """Create a FAISS vector store from the documents."""
        if not self.documents:
            raise ValueError("No documents loaded. Please run load_documents() first.")
        if not hasattr(self, 'embedding_model'):
            raise ValueError("No embedding model set. Please run set_embedding_model() first.")

        print("Creating FAISS vector store...")
        self.vector_store = FAISS.from_documents(self.documents, self.embedding_model)
        self.vector_store.save_local(save_path)
        print(f"FAISS index saved to '{save_path}' directory.")

    def load_vector_store(self, load_path="faiss_index"):
        """Load an existing FAISS vector store."""
        print(f"Loading FAISS vector store from '{load_path}'...")
        self.vector_store = FAISS.load_local(load_path, self.embedding_model)
        print("FAISS vector store loaded successfully.")
