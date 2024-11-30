import os
from os import mkdir
import torch
import torch
from tree_sitter import Language, Parser
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import SystemMessage, HumanMessage
from transformers import AutoTokenizer, AutoModelForCausalLM
import weaviate

HF_TOKEN = os.getenv('HF_TOKEN')

def get_weaviate_client():
    """
    Initialize the Weaviate client with the latest syntax.
    """
    client = weaviate.connect_to_local(port=8090, skip_init_checks=True)
    if not client.is_ready():
        raise ConnectionError("Failed to connect to Weaviate.")
    return client

class CodeProcessor:
    def __init__(self, weaviate_url, gemini_model_name="gemini-1.5-flash", languages=None):
        self.client = get_weaviate_client()
        self.gemini_llm = ChatGoogleGenerativeAI(model=gemini_model_name)
        self.tokenizer = AutoTokenizer.from_pretrained("bigcode/starcoder", token=HF_TOKEN)
        self.model = AutoModelForCausalLM.from_pretrained(
            "bigcode/starcoder", token=HF_TOKEN, device_map="auto"
        )

        self.parsers = {}
        self.supported_languages = languages or {
            "python": "tree-sitter-python",
            "cpp": "tree-sitter-cpp"
        }
        self.build_and_load_parsers()
        self.create_schema()

    def build_and_load_parsers(self):
        if not os.path.exists("build"):
            os.mkdir("build")
        Language.build_library(
            "build/my-languages.so", 
            [f"./{lang_dir}" for lang_dir in self.supported_languages.values()]
        )
        for lang_name, lang_dir in self.supported_languages.items():
            lang = Language("build/my-languages.so", lang_name)
            parser = Parser()
            parser.set_language(lang)
            self.parsers[lang_name] = parser

    def create_schema(self):
        """
        Create the schema for the Weaviate database if it does not already exist.
        """
        schema = {
            "class": "CodeSnippet",
            "description": "A snippet of code from a repository",
            "properties": [
                {"name": "repository", "dataType": ["string"], "description": "Repository name"},
                {"name": "file_path", "dataType": ["string"], "description": "File path"},
                {"name": "function_name", "dataType": ["string"], "description": "Function name"},
                {"name": "class_name", "dataType": ["string"], "description": "Class name"},
                {"name": "code", "dataType": ["text"], "description": "Raw code"},
                {"name": "docstring", "dataType": ["text"], "description": "Generated docstring"},
                {"name": "imports", "dataType": ["text"], "description": "Import statements"},
                {"name": "global_variables", "dataType": ["text"], "description": "Global variables"}
            ],
            "vectorizer": "none"
        }
        if not self.client.schema.contains(schema):
            self.client.schema.create_class(schema)

    def parse_code(self, file_path: str, language: str):
        if language not in self.parsers:
            raise ValueError(f"Unsupported language: {language}")

        parser = self.parsers[language]
        with open(file_path, "r") as f:
            code = f.read()
        tree = parser.parse(bytes(code, "utf8"))
        return code, tree.root_node

    def extract_imports(self, code: str):
        return "\n".join(line for line in code.splitlines() if line.startswith("import") or line.startswith("from"))

    def extract_global_variables(self, code: str) -> str:
        return "\n".join(
            line for line in code.splitlines() if "=" in line and not line.startswith(" ")
        )

    def extract_code_units(self, code: str, root_node, language: str):
        """Extract functions, methods, or classes from the code, including class context."""
        if language == "python":
            types = {"function_definition", "class_definition"}
        elif language == "cpp":
            types = {"function_definition", "class_specifier"}
        else:
            raise ValueError(f"Unsupported language for extraction: {language}")

        code_units = []
        current_class = None
        for node in root_node.children:
            if node.type == "class_definition" and language == "python":
                current_class = {
                    "name": node.child_by_field_name("name").text.decode(),
                    "body": code[node.start_byte:node.end_byte],
                }
            elif node.type in types:
                unit_code = code[node.start_byte:node.end_byte]
                code_units.append({
                    "code": unit_code,
                    "class_context": current_class,
                    "node": node,
                })
        return code_units


    def generate_docstring(self, code_snippet: str, language: str):
        prompt = (
            f"Generate a docstring for the following {len(code_snippet.splitlines())}-line code "
            f"written in {language}:\n\n{code_snippet}"
        )
        messages = [
            SystemMessage(content="You are an AI assistant that generates helpful docstrings for code."),
            HumanMessage(content=prompt)
        ]
        response = self.gemini_llm.invoke(messages)
        return response.content.strip()

    def generate_embedding(self, context: str):
        inputs = self.tokenizer(context, return_tensors="pt", truncation=True, max_length=8192)
        with torch.no_grad():
            outputs = self.model(**inputs)
        return outputs.last_hidden_state.mean(dim=1).squeeze().cpu().numpy()

    def process_repository(self, repo_path: str, language: str):
        """Process a repository and ingest code snippets with class context into Weaviate."""
        for root, _, files in os.walk(repo_path):
            for file in files:
                if file.endswith(".py") or file.endswith((".cpp", ".hpp", ".h")):
                    file_path = os.path.join(root, file)
                    code, root_node = self.parse_code(file_path, language)
                    imports = self.extract_imports(code)
                    globals_ = self.extract_global_variables(code)
                    code_units = self.extract_code_units(code, root_node, language)
                    self.ingest_code_units(code_units, imports, globals_, file_path, language)


    def ingest_code_units(self, code_units, imports, globals_, file_path, language):
        """Ingest code units into Weaviate, handling chunking and class context."""
        for unit in code_units:
            code_unit = unit["code"]
            class_context = unit["class_context"]

            # Add class context to the embedding context if available
            context = f"{imports}\n\n{globals_}\n\n"
            if class_context:
                context += f"class {class_context['name']}:\n{class_context['body']}\n\n"

            context += code_unit

            # Generate docstring and embedding
            docstring = self.generate_docstring(code_unit, language)
            chunks = self.chunk_code(context, max_length=8192)

            for i, chunk in enumerate(chunks):
                embedding = self.generate_embedding(chunk)
                chunk_id = f"{file_path}:{i+1}" if len(chunks) > 1 else file_path

                # Create the data object
                data_object = {
                    "repository": os.path.basename(file_path),
                    "file_path": file_path,
                    "function_name": None,
                    "class_name": class_context["name"] if class_context else None,
                    "code": chunk,
                    "docstring": docstring if i == 0 else "(continued...)",
                    "imports": imports,
                    "global_variables": globals_,
                }

                # Ingest the data object into Weaviate
                self.client.data_object.create(data_object, "CodeSnippet", vector=embedding)


    def chunk_code(self, context: str, max_length: int = 8192):
        """Chunk a code snippet into smaller pieces that fit within the model's context."""
        input_ids = self.tokenizer(context, return_tensors="pt")["input_ids"].squeeze(0)
        if len(input_ids) <= max_length:
            return [context]  # No need to chunk

        chunks = []
        current_chunk = []
        current_length = 0

        # Split context into lines and process line by line
        for line in context.splitlines():
            tokenized_line = self.tokenizer(line, return_tensors="pt")["input_ids"].squeeze(0)
            line_length = len(tokenized_line)
            if current_length + line_length > max_length:
                # If adding this line exceeds max length, start a new chunk
                chunks.append("\n".join(current_chunk))
                current_chunk = [line]
                current_length = line_length
            else:
                current_chunk.append(line)
                current_length += line_length

        # Append the last chunk
        if current_chunk:
            chunks.append("\n".join(current_chunk))

        return chunks



# Example Usage
if __name__ == "__main__":
    processor = CodeProcessor("http://localhost:8090")
    processor.process_repository("$HOME/projects/ai-assistant", "python")
    processor.process_repository("$HOME/projects/Gopher", "python")
    processor.process_repository("$HOME/projects/StuckFish", "cpp")
