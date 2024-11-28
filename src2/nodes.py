from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
import torch
from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings
import json
from config import CONFIG

# Define the state structure
class State(TypedDict):
    messages: Annotated[list, add_messages]

# Node definitions
def query_node(state: State):
    """Node to accept user input."""
    query = state["messages"][-1][1]  # Last user input
    if not query:
        raise ValueError("No query provided.")
    state["messages"].append(("query", query))
    return state

class RetrievalNode(Node):
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(model_name=CONFIG["retriever_model"])
        self.vector_store = FAISS.load_local(CONFIG["vector_store_path"], self.embeddings)

    def run(self, state: State):
        query = state["messages"][-1][1]  # Get the query
        top_k = 5  # Number of documents to retrieve
        
        # Perform similarity search
        retrieved_docs = self.vector_store.similarity_search(query, k=top_k)
        
        # Pass retrieved docs with metadata into the pipeline
        results = [
            {"content": doc.page_content, "metadata": doc.metadata}
            for doc in retrieved_docs
        ]
        state["messages"].append(("retrieved_docs", results))
        return state


class SummarizationNode(Node):
    def __init__(self):
        self.summarizer = pipeline("summarization", model=CONFIG["summarizer_model"])

    def run(self, state: State):
        retrieved_docs = state["messages"][-1][1]  # Retrieved documents
        combined_text = " ".join(retrieved_docs)
        
        # Summarize the combined text
        summary = self.summarizer(combined_text, max_length=512, min_length=100, truncation=True)
        state["messages"].append(("summary", summary[0]["summary_text"]))
        return state


def prompt_node(state: State):
    """Node to construct a prompt."""
    query = state["messages"][0][1]  # User query
    summary = state["messages"][-1][1]  # Summarized context
    
    prompt = (
        f"You are an AI assistant with knowledge of the user's projects.\n\n"
        f"Context:\n{summary}\n\n"
        f"Question: {query}\n\n"
        f"Please provide a clear and concise response."
    )
    state["messages"].append(("prompt", prompt))
    return state




class LLMNode(Node):
    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained(CONFIG["llm_model"])
        self.model = AutoModelForCausalLM.from_pretrained(CONFIG["llm_model"])
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)

    def run(self, state: State):
        prompt = state["messages"][-1][1]  # Get the prompt
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=CONFIG["max_context_tokens"])
        inputs = inputs.to(self.device)
        
        outputs = self.model.generate(
            input_ids=inputs["input_ids"],
            max_new_tokens=CONFIG["response_percentage"],
            temperature=0.7,
            top_p=0.9,
            pad_token_id=self.tokenizer.eos_token_id,
        )
        
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        state["messages"].append(("response", response))
        return state


def output_node(state: State):
    """Node to output the final response."""
    response = state["messages"][-1][1]  # Get the response
    print("\nAI Assistant Response:\n", response)
    return state


