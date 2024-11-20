import argparse
import streamlit as st
from embedding_manager import EmbeddingManager
from llm_manager import LLMManager
from rag_pipeline import RAGPipeline



def initialize_components(index_path, model_name, device, top_k):
    """
    Initialize the main components of the app: EmbeddingManager, LLMManager, RAGPipeline.

    :param index_path: Path to the FAISS index.
    :param model_name: Name of the LLM model to use.
    :param device: Device for inference ('cuda' or 'cpu').
    :param top_k: Number of results to retrieve for each query.
    :return: Initialized instances of RAGPipeline and its components.
    """
    # Initialize EmbeddingManager
    embedding_manager = EmbeddingManager(model_name="all-MiniLM-L6-v2")
    embedding_manager.load_index(index_path)

    # Initialize LLMManager
    llm_manager = LLMManager(model_name=model_name, device=device)

    # Initialize RAGPipeline
    rag_pipeline = RAGPipeline(embedding_manager, llm_manager, top_k=top_k)

    return embedding_manager, llm_manager, rag_pipeline


def cli_mode(rag_pipeline):
    """
    Run the app in CLI mode.

    :param rag_pipeline: Instance of RAGPipeline to handle queries.
    """
    print("\nWelcome to the AI Assistant (RAG Pipeline)")
    print("Type 'exit' to quit.\n")

    while True:
        query = input("Enter your query: ")
        if query.lower() == "exit":
            print("Goodbye!")
            break

        try:
            response = rag_pipeline.query(query)
            print("\nResponse:")
            print(response[:2000])  # Print only the first 2000 characters for long responses
            if len(response) > 2000:
                print("\n[Response truncated. Consider refining your query.]")
            print("\n" + "-" * 50)
        except Exception as e:
            print(f"Error processing your query: {e}")



def streamlit_mode(rag_pipeline):
    """
    Run the app in Streamlit UI mode.

    :param rag_pipeline: Instance of RAGPipeline to handle queries.
    """
    st.title("AI Assistant - RAG Pipeline")
    st.subheader("Retrieve context-enhanced AI responses using FAISS and LLMs.")

    query = st.text_input("Enter your query:")
    if query:
        with st.spinner("Processing..."):
            response = rag_pipeline.query(query)
        st.subheader("Response:")
        st.write(response)


def main():
    """
    Main entry point for the app. Handles argument parsing and mode selection.
    """
    parser = argparse.ArgumentParser(description="AI Assistant with RAG Pipeline")
    parser.add_argument(
        "--index_path",
        type=str,
        default="data/embeddings/ChatGPT_index.faiss",
        help="Path to the FAISS index file.",
    )
    parser.add_argument(
        "--model_name",
        type=str,
        default="EleutherAI/gpt-neo-1.3B",
        help="Name of the Hugging Face model to use.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda",
        help="Device to use for inference ('cuda' or 'cpu').",
    )
    parser.add_argument(
        "--top_k",
        type=int,
        default=5,
        help="Number of top results to retrieve for each query.",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="cli",
        choices=["cli", "streamlit"],
        help="Mode to run the app ('cli' or 'streamlit').",
    )
    args = parser.parse_args()

    # Initialize components
    embedding_manager, llm_manager, rag_pipeline = initialize_components(
        index_path=args.index_path,
        model_name=args.model_name,
        device=args.device,
        top_k=args.top_k,
    )

    # Choose mode
    if args.mode == "cli":
        cli_mode(rag_pipeline)
    elif args.mode == "streamlit":
        streamlit_mode(rag_pipeline)


if __name__ == "__main__":
    main()
