from google.generativeai import generate_embeddings

embedding_response = generate_embeddings(
    model="gemini-pro", texts=["Text for embedding."]
)
embedding = embedding_response['embeddings'][0]
