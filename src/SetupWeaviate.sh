#/usr/bin/bash
git clone https://github.com/tree-sitter/tree-sitter-python.git
docker pull semitechnologies/weaviate:latest
docker run -d -p 8090:8080 semitechnologies/weaviate:latest
curl -X POST "http://localhost:8090/v1/schema" \
-H "Content-Type: application/json" \
-d '{
    "class": "CodeSnippet",
    "description": "A snippet of code from a repository",
    "properties": [
        {"name": "repository", "dataType": ["string"], "description": "Repository name"},
        {"name": "file_path", "dataType": ["string"], "description": "File path"},
        {"name": "function_name", "dataType": ["string"], "description": "Function name"},
        {"name": "class_name", "dataType": ["string"], "description": "Class name"},
        {"name": "code", "dataType": ["text"], "description": "Raw code"},
        {"name": "docstring", "dataType": ["text"], "description": "Docstring"}
    ],
    "vectorizer": "none"
}'
