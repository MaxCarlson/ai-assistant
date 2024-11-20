import streamlit as st
from embedding_manager import EmbeddingManager
from llm_manager import LLMManager
from rag_pipeline import RAGPipeline

# Initialize the components
embedding_manager = EmbeddingManager(model_name="all-MiniLM-L6-v2")
embedding_manager.load_index("ChatGPT_index.faiss")

llm_manager = LLMManager(model_name="EleutherAI/gpt-neo-1.3B")
rag_pipeline = RAGPipeline(embedding_manager, llm_manager)

# Streamlit UI
st.title("AI Assistant - RAG Pipeline")

query = st.text_input("Enter your query:")
if query:
    with st.spinner("Processing..."):
        response = rag_pipeline.query(query)
    st.subheader("Response:")
    st.write(response)
