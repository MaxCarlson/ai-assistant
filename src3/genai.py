from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from rag_manager import RAGManager
from settings import MAX_TOKENS
from token_manager import TokenManager


# Initialize the LLM
llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro")
#llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-8b")
#llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
#llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")



# System message template
system_template = "You are an AI assistant. Use the following context to help answer the user's query:\n{context}\n"

# Initialize components
rag_manager = RAGManager("gemini-1.5-pro", "all-MiniLM-L6-v2")
token_manager = TokenManager()
conversation_history = []

def chat():
    global conversation_history
    while True:
        user_input = input("You: ")
        
        # Retrieve relevant context
        context = rag_manager.get_context(user_input, conversation_history)
        
        # Limit tokens for conversation history and context
        conversation_history, context = token_manager.limit_tokens(
            user_input=user_input,
            conversation_history=conversation_history,
            context=context,
            max_tokens=MAX_TOKENS,
            percent_context=0.35  # RAG context capped at 35%
        )
        
        # Create the system message content with context
        system_message = system_template.format(context=context)
        
        # Build the list of messages manually
        messages = [{"role": "system", "content": system_message}]
        for entry in conversation_history:
            messages.append({"role": entry["role"], "content": entry["content"]})
        messages.append({"role": "user", "content": user_input})
        
        # Debug: Print the constructed messages
        #print("Constructed Messages:", messages)
        
        # Invoke the LLM
        response = llm.invoke(messages)
        
        # Add the assistant's response to the history
        conversation_history.append({"role": "assistant", "content": response.content})
        
        # Print the response
        print(f"Assistant: {response.content}")



if __name__ == "__main__":
    chat()
