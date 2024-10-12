import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY_AI_ASSISTANT')

# Initialize the Gemini Pro model
llm = ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=GOOGLE_API_KEY)

# Create a prompt template
template = PromptTemplate.from_template("Describe {topic}.")
chain = LLMChain(llm=llm, prompt=template)

# Example usage
result = chain.run(topic="the future of AI")
print(result)