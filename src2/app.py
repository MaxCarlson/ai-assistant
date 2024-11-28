from langgraph.graph import StateGraph, START, END
from nodes import State, query_node, retrieval_node, summarization_node, prompt_node, llm_node, output_node

def create_pipeline():
    
    # Create the LangGraph builder
    graph_builder = StateGraph(State)

    # Build the graph
    graph_builder.add_node("query", query_node)
    graph_builder.add_node("retrieval", retrieval_node)
    graph_builder.add_node("summarization", summarization_node)
    graph_builder.add_node("prompt", prompt_node)
    graph_builder.add_node("llm", llm_node)
    graph_builder.add_node("output", output_node)

    # Define edges between nodes
    graph_builder.add_edge(START, "query")
    graph_builder.add_edge("query", "retrieval")
    graph_builder.add_edge("retrieval", "summarization")
    graph_builder.add_edge("summarization", "prompt")
    graph_builder.add_edge("prompt", "llm")
    graph_builder.add_edge("llm", "output")
    graph_builder.add_edge("output", END)

    # Compile the graph
    graph = graph_builder.compile()

    return graph

# Main loop
def main():
    """Main interactive loop for the AI Assistant."""
    print("Welcome to the AI Assistant!")
    print("Type 'exit' to quit.\n")
    graph = create_pipeline()
    
    while True:
        initial_state = {"messages": []}
        user_query = input("Enter your query: ")
        if user_query.lower() == "exit":
            print("Goodbye!")
            break
        # Inject the user query into the initial state
        initial_state["messages"].append(("user", user_query))
        
        # Run the graph
        graph.invoke(initial_state)

if __name__ == "__main__":
    main()
