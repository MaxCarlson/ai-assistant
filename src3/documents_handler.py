from abc import ABC, abstractmethod
from enum import Enum
import PyPDF2
import google.generativeai as genai
import docx
from typing import List

class DocumentType(Enum):
    PDF = 1
    DOCX = 2
    TXT = 3
    
class DocumentPrompts(Enum):
    SUMMARIZE = "Summarize the document"
    BRIEF_SUMMARY = "Briefly summarize the document"
    RE_WRITE = "Re-write the document in a more concise manner without losing the main points"
    
class TextExtractor(ABC):
    @abstractmethod
    def extract_text(self, file_path):
        pass
    
class PDFTextExtractor(TextExtractor):
    def extract_text(self, file_path):
        with open(file_path, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            extracted_text = ""
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    extracted_text += text
            return extracted_text

class TXTTextExtractor(TextExtractor):
    def extract_text(self, file_path):
        with open(file_path, 'r') as txt_file:
            return txt_file.read()

# Assuming DOCX handling via python-docx (not implemented here)
class DOCXTextExtractor(TextExtractor):
    def extract_text(self, file_path):
        doc = docx.Document(file_path)
        extracted_text = ""
        for para in doc.paragraphs:
            extracted_text += para.text + "\n"
        return extracted_text
       
class DocumentLoader:
    def __init__(self, document_path: str, doc_type: DocumentType):
        self.document_path = document_path
        self.doc_type = doc_type
        self.doc = None

        if self.doc_type == DocumentType.PDF:
            self.doc = PDFTextExtractor().extract_text(self.document_path)
        elif self.doc_type == DocumentType.TXT:
            self.doc = TXTTextExtractor().extract_text(self.document_path)
        elif self.doc_type == DocumentType.DOCX:
            self.doc = DOCXTextExtractor().extract_text(self.document_path)
        else:
            raise ValueError("Unsupported document type")
    
class ModelHandler:
    def __init__(self, model_type):
        self.model_type = model_type
        
    def process(self, prompt, docs: List[DocumentLoader]):
        if self.model_type is genai.GenerativeModel:
            inputs = [prompt.value] + [doc.doc for doc in docs]
            return self.model_type.generate_content(inputs)
        else:
            raise ValueError("Unsupported model_type type")

class DocumentHandler:
    
    def __init__(self, model, doc_prompt: DocumentPrompts, doc_loaders: List[DocumentLoader]):
        self.model = model
        self.doc_prompt = doc_prompt
        self.doc_loaders = doc_loaders
        
    def handle_documents(self):
        return ModelHandler(self.model).process(self.doc_prompt, self.doc_loaders)
    
