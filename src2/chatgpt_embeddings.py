from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings
from ChatGPTConversions import ChatGPTConversations
from settings import EMBEDDINGS_DIRECTORY

# Initialize utilities
embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1024, chunk_overlap=50)

# Load and process conversations
converter = ChatGPTConversations("data/ChatGPT-2024-10-12-10-05-59/conversations.json")
chats = converter.get_conversations()

documents = []
for chat in chats:
    full_text = "\n".join([f"{msg['author']}: {msg['content']}" for msg in chat["messages"]])
    chunks = text_splitter.split_text(full_text)
    for chunk in chunks:
        documents.append(Document(page_content=chunk, metadata={"chat_id": chat.get("id", "unknown"), "source": "ChatGPT"}))

# Create and save the FAISS vector store
vector_store = FAISS.from_documents(documents, embedding_model)
vector_store.save_local(EMBEDDINGS_DIRECTORY + "ChatGPT_index")
print("FAISS index created and saved successfully.")
