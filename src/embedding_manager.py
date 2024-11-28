import json
import os
import numpy as np
import json
import faiss
from sentence_transformers import SentenceTransformer



class EmbeddingManager:
    """
    A modular class to handle vector database queries and retrieval.
    Ensures embedding model consistency.
    """

    def __init__(
        self, model_name="all-MiniLM-L6-v2", index_type="FlatL2", embedding_dim=384
    ):
        """
        Initialize the Retriever.

        :param model_name: Name of the SentenceTransformer model for embedding creation.
        :param index_type: Type of FAISS index (e.g., "FlatL2", "IVFFlat").
        :param embedding_dim: Dimensionality of embeddings (default: 384).
        """
        self.embedding_model = SentenceTransformer(model_name)
        self.embedding_model = self.embedding_model.to("cuda")  # Move model to GPU
        self.model_name = model_name
        self.index_type = index_type
        self.embedding_dim = embedding_dim
        self.index = None
        self.metadata = {}  # A dictionary to store document metadata

    def create_index(self, index_type="FlatL2"):
        """
        Create a new FAISS index and store model metadata.

        :param index_type: Type of FAISS index to use.
        """
        if index_type == "FlatL2":
            self.index = faiss.IndexFlatL2(self.embedding_dim)
        elif index_type == "FlatIP":
            self.index = faiss.IndexFlatIP(
                self.embedding_dim
            )  # Inner Product (Cosine Similarity)
        else:
            raise ValueError(f"Unsupported index type: {index_type}")
        print(f"FAISS index of type {index_type} created.")

    def load_index(self, index_path):
        """
        Load a FAISS index and model metadata from a file.
        """
        if not os.path.exists(index_path):
            raise FileNotFoundError(f"FAISS index file not found: {index_path}")
        
        # Load the FAISS index
        self.index = faiss.read_index(index_path)

        # Load metadata
        metadata_path = index_path.replace(".faiss", ".meta.json")
        if os.path.exists(metadata_path):
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
                self.model_name = metadata["model_name"]
                self.index_type = metadata["index_type"]
                self.embedding_dim = metadata["embedding_dim"]
                self.metadata["documents"] = metadata.get("documents", {})
        else:
            print(f"No metadata file found for {index_path}. Metadata will not be loaded.")
            self.metadata["documents"] = {}

        print(f"FAISS index and metadata loaded from {index_path}.")


    def save_index(self, index_path):
        """
        Save the current FAISS index and model metadata to a file.
        """
        if self.index is None:
            raise RuntimeError("No index to save. Create or load an index first.")
        
        # Save the FAISS index
        faiss.write_index(self.index, index_path)

        # Save metadata, including documents
        metadata_path = index_path.replace(".faiss", ".meta.json")
        metadata = {
            "model_name": self.model_name,
            "index_type": self.index_type,
            "embedding_dim": self.embedding_dim,
            "documents": self.metadata.get("documents", {}),
        }
        with open(metadata_path, "w") as f:
            json.dump(metadata, f)

        print(f"FAISS index and metadata saved to {index_path} and {metadata_path}.")


    def add_documents(self, documents):
        """
        Add documents to the index after creating embeddings.
        Ensures model consistency.

        :param documents: List of strings (documents to add).
        """
        if self.index is None:
            raise RuntimeError("Create or load an index before adding documents.")

        # Create embeddings
        embeddings = self.embedding_model.encode(documents, convert_to_numpy=True)

        # Add embeddings to the FAISS index
        self.index.add(embeddings)

        # Store metadata (e.g., document content or additional info)
        for i, doc in enumerate(documents):
            self.metadata[self.index.ntotal - len(documents) + i] = {"content": doc}

        print(f"{len(documents)} documents added to the index.")

    def query(self, text, top_k=5):
        """
        Query the index with a text input.

        :param text: Input query text.
        :param top_k: Number of top results to return.
        :return: List of results with metadata and distances.
        """
        if self.index is None:
            raise RuntimeError("Create or load an index before querying.")

        # Generate query embedding
        query_embedding = self.embedding_model.encode([text], convert_to_numpy=True)

        # Ensure correct query shape
        query_embedding = query_embedding.reshape(1, -1)

        # Perform FAISS search
        distances, indices = self.index.search(query_embedding, top_k)

        # Retrieve results
        results = []
        for i, idx in enumerate(indices[0]):
            if idx == -1:
                results.append({"content": "No content available", "distance": None})
            else:
                # Access metadata from self.metadata["documents"]
                document_metadata = self.metadata.get("documents", {}).get(str(idx), {})
                document_metadata["distance"] = distances[0][i]
                results.append(document_metadata)

        return results

    def debug_query(self, query, top_k=5):
        """
        Run a query against the FAISS database and inspect the retrieved results.
        """
        if self.index is None:
            raise RuntimeError("No FAISS index is loaded. Please load or create an index first.")
        
        if "documents" not in self.metadata or len(self.metadata["documents"]) != self.index.ntotal:
            raise ValueError(
                f"Number of documents ({len(self.metadata.get('documents', {}))}) does not match "
                f"number of vectors in FAISS index ({self.index.ntotal})."
            )

        # Generate query embedding
        query_embedding = self.embedding_model.encode(query, convert_to_tensor=True).cpu().numpy().reshape(1, -1)
        distances, indices = self.index.search(query_embedding, top_k)

        # Retrieve results
        results = []
        for i, idx in enumerate(indices[0]):
            if idx == -1:  # No valid result
                results.append({
                    "rank": i + 1,
                    "content": "No content available",
                    "score": None,
                })
            else:
                metadata = self.metadata["documents"].get(str(idx), {})
                results.append({
                    "rank": i + 1,
                    "content": metadata.get("content", "No content available"),
                    "score": distances[0][i],
                })

        return results




