import os
import numpy as np
import requests
import faiss
from dotenv import load_dotenv
from transformers import GPT2TokenizerFast
from ChatGPTConversions import ChatGPTConversations
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from sentence_transformers import SentenceTransformer
from alive_progress import alive_bar
from settings import EMBEDDINGS_DIRECTORY
from embedding_manager import EmbeddingManager

# import torch

# Define the scope required for the Generative Language API
# SCOPES = ['https://www.googleapis.com/auth/generative-language']
#
## Path to your OAuth credentials file
# CLIENT_SECRET_FILE = 'oauth2_credentials.json'
#
## Authenticate using OAuth 2.0
# flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
# creds = flow.run_local_server(port=0)
#
## Use the access token in headers for API requests
# headers = {
#    'Authorization': f'Bearer {creds.token}',
#    'Content-Type': 'application/json'
# }

# Define the embedding model URL
# embedding_model_url = "https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent"
#
## Function to generate embeddings
# def generate_embedding(text_chunk):
#    response = requests.post(embedding_model_url, headers=headers, json={
#        "model": "models/text-embedding-004",
#        "content": {"parts": [{"text": text_chunk}]},
#        "task_type": "retrieval_document"
#    })
#    if response.status_code == 200:
#        return response.json().get("embedding", [])
#    else:
#        raise Exception(f"Error {response.status_code}: {response.text}")
#

retriever = EmbeddingManager(
    model_name="all-MiniLM-L6-v2", index_type="FlatL2", embedding_dim=384
)


# Load a Sentence Transformer model with GPU support for embeddings
# embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
# embedding_model = embedding_model.to("cuda")  # Move model to GPU


# Function to generate embeddings using the local Sentence Transformer model
def generate_embedding(text_chunk):
    # Ensure the text chunk is converted to the format the model expects
    embeddings = retriever.embedding_model.encode(
        text_chunk, convert_to_tensor=True, device="cuda"
    )
    return embeddings.cpu().numpy()  # Move embeddings back to CPU if needed


# Initialize the GPT-2 tokenizer for token counting
max_tokens = 1024
tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")


# Helper function to chunk text by character length first, then tokenize within limits
def adaptive_chunk_text_by_tokens(
    text, max_tokens, tokenizer, initial_chars_per_token=4
):
    chunks = []
    start_idx = 0

    while start_idx < len(text):
        # Start with an optimistic chunk size based on initial_chars_per_token
        chars_per_token = initial_chars_per_token
        end_idx = min(len(text), start_idx + max_tokens * chars_per_token)
        chunk = text[start_idx:end_idx]

        # Tokenize and check if the chunk meets the token limit
        tokens = tokenizer.encode(chunk)
        while len(tokens) > max_tokens:
            # If the chunk is too large, decrease chars_per_token conservatively
            chars_per_token -= 0.5
            end_idx = min(len(text), start_idx + int(max_tokens * chars_per_token))
            chunk = text[start_idx:end_idx]
            tokens = tokenizer.encode(chunk)

            # Safety check to avoid infinite loop if chars_per_token becomes too small
            if chars_per_token < 1.5:
                # Break by tokens if chars_per_token is too small and chunk is still too large
                token_chunks = [
                    tokens[i : i + max_tokens]
                    for i in range(0, len(tokens), max_tokens)
                ]
                chunks.extend(
                    [tokenizer.decode(token_chunk) for token_chunk in token_chunks]
                )
                start_idx = end_idx  # Move to the next chunk position
                break
        else:
            # If the chunk fits within the token limit, add it to chunks
            chunks.append(chunk)
            start_idx = end_idx  # Move to the next chunk position

    return chunks


# Load ChatGPT conversations
converter = ChatGPTConversations("data/ChatGPT-2024-10-12-10-05-59/conversations.json")
chats = converter.get_conversations()

# Process each chat and generate embeddings
print("Creating Chat Embeddings")
all_text_chunks = []  # Keep track of all chunks for metadata
with alive_bar(len(chats)) as bar:
    for chat in chats:
        # Combine messages from chat based on author and content
        combined_content = []
        for message in chat["messages"]:
            author = message["author"]
            content = message["content"]
            combined_content.append(f"{author}: {content}")

        # Join all messages into one string (a full conversation)
        full_conversation = "\n".join(combined_content)

        # Chunk conversation text into manageable sizes
        conversation_chunks = adaptive_chunk_text_by_tokens(
            full_conversation, max_tokens, tokenizer
        )
        all_text_chunks.extend(conversation_chunks)  # Store chunks for metadata

        bar()

# Add all chunks to the retriever and create embeddings
retriever.create_index()  # Ensure an index is created
retriever.add_documents(all_text_chunks)

# Save the FAISS index for future use
retriever.save_index(EMBEDDINGS_DIRECTORY + "ChatGPT_index.faiss")
print("ChatGPT embeddings indexed and saved successfully.")
