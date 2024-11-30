# test_weaviate.py
import weaviate

client = weaviate.Client("http://localhost:8090")
print(client.is_ready())
