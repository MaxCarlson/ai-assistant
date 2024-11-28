from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings  # Updated import
from langchain_community.vectorstores import FAISS
from langchain.schema import Document
import os
from alive_progress import alive_bar

# Path to your notes directory
notes_dir = os.path.expanduser("/mnt/c/Users/mcarls/Documents/Obsidian-Vault")

# Initialize a text splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=50,
    separators=["\n\n", "\n", " "]
)

# Initialize HuggingFaceEmbeddings with a SentenceTransformer model
embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Process each note and split into chunks
documents = []
files = [f for f in os.listdir(notes_dir) if os.path.isfile(os.path.join(notes_dir, f))]

print("Processing files...")
with alive_bar(len(files)) as file_bar:
    for file_name in files:
        file_path = os.path.join(notes_dir, file_name)
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            chunks = text_splitter.split_text(content)
            for chunk in chunks:
                documents.append(Document(page_content=chunk))
        file_bar()

# Create a FAISS vector store from the documents using the embedding model
print("Creating FAISS vector store...")
vector_store = FAISS.from_documents(documents, embedding_model)

# Save the FAISS index locally
vector_store.save_local("faiss_index")
print("FAISS index saved to 'faiss_index' directory.")
