from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

# Initialize the language model
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-8b")

# Define the system message template
system_template = "You are an AI assistant."

# Create the chat prompt template
prompt_template = ChatPromptTemplate.from_messages(
    [("system", system_template), ("user", "{user_input}")]
)

def chat():
    while True:
        # Get user input
        user_input = input("You: ")
        
        # Format the prompt with the user input
        prompt = prompt_template.format_prompt(user_input=user_input)
        
        # Convert the prompt to a list of messages
        messages = prompt.to_messages()
        
        # Invoke the language model with the messages
        response = llm.invoke(messages)
        
        # Print the assistant's response
        print(f"Assistant: {response.content}")

if __name__ == "__main__":
    chat()
