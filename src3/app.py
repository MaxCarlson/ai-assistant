import os
from langchain.chains import Chain
from langchain.schema import Response
from langchain.clients import LocalTransformersClient
from langchain.retrieval import InMemoryRetriever
import google.generativeai as genai
from abc import ABC, abstractmethod

# Define a custom function to handle Gemini model interactions
def gemini_model_query(prompt, max_tokens=200):
    # Assuming `model` and `chat_session` from your Gemini setup
    response = chat_session.send_message(prompt, stream=True, generation_config={
        "candidate_count": 1,
        "max_output_tokens": max_tokens,
        "temperature": 1.0,
    })
    return Response(text="".join(part.text for part in response))

class ModelBase(ABC):
    @abstractmethod
    def generate_response(self, prompt: str) -> str:
        pass

class GeminiModelHandler(ModelBase):
    def __init__(self, model_name="gemini-1.5-flash-8b"):
        # Configure the API using the environment variable
        self.api_key = os.getenv('GOOGLE_API_KEY_AI_ASSISTANT')
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        self.chat_session = self.model.start_chat(history=[])
    
    def generate_response(self, prompt, docs: List[DocumentLoader] = None):
        response = self.chat_session.send_message(prompt, stream=True, generation_config={
            "candidate_count": 1,
            "max_output_tokens": 200,
            "temperature": 1.0,
        })
        return "".join(part.text for part in response)


# Initialize the client with the custom query function
client = LocalTransformersClient(query_fn=gemini_model_query)

# Set up the LangChain with this client
chain = Chain(client)


# Simulate a retrieval system
retriever = InMemoryRetriever(documents={
    "doc1": "Information about project Alpha",
    "doc2": "Details on project Beta"
})

# Update the chain to use this retriever
chain.set_retriever(retriever)

def chat_with_rag():
    print("Chatbot with RAG is ready. Type 'quit' to exit.")
    while True:
        user_input = input("You: ")
        if user_input.lower() == 'quit':
            break
        response = chain.query(user_input)
        print("Bot:", response.text)

if __name__ == "__main__":
    chat_with_rag()
