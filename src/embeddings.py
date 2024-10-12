from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from dotenv import load_dotenv
import os
from ChatGPTConversions import ChatGPTConversations
from transformers import GPT2TokenizerFast

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY_AI_ASSISTANT')

max_tokens = 4096

# Initialize the GPT-2 tokenizer for token counting
tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")

# Initialize the Gemini Pro model for chat and embedding purposes
llm = ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=GOOGLE_API_KEY)

# Helper function to split conversation into chunks based on token limit
def chunk_text_by_tokens(text, max_tokens, tokenizer):
    tokens = tokenizer.encode(text)
    chunks = []
    
    # Split tokens into chunks based on max_tokens limit
    for i in range(0, len(tokens), max_tokens):
        chunk_tokens = tokens[i:i + max_tokens]
        chunk_text = tokenizer.decode(chunk_tokens)
        chunks.append(chunk_text)
    
    return chunks

# Load ChatGPT conversations
converter = ChatGPTConversations('data/ChatGPT-2024-10-12-10-05-59/conversations.json')
chats = converter.get_conversations()

all_embeddings = []

# Loop through each chat
for chat in chats:
    # Combine messages from chat based on author and content
    combined_content = []
    
    for message in chat['messages']:  # Assuming chat['messages'] contains individual messages
        author = message['author']
        content = message['content']
        combined_content.append(f"{author}: {content}")
    
    # Join all messages into one string (a full conversation)
    full_conversation = "\n".join(combined_content)

    # Tokenize and chunk conversation if needed
    num_tokens = len(tokenizer.encode(full_conversation))
    
    if num_tokens > max_tokens:
        # Chunk the conversation into smaller parts
        conversation_chunks = chunk_text_by_tokens(full_conversation, max_tokens, tokenizer)
    else:
        # If it's within the limit, process it as a single chunk
        conversation_chunks = [full_conversation]

    # Generate embeddings for each chunk and store them
    for chunk in conversation_chunks:
        response = llm.invoke(chunk)
        embedding = response.content  # The content field holds the response embedding or output
        all_embeddings.append(embedding)

# Check the first embedding
print(all_embeddings[0])
