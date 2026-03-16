# rag_engine.py
import os
from threading import Lock
from collections import deque
from dotenv import load_dotenv
from llama_index.core import (
    VectorStoreIndex,
    Settings,
    SimpleDirectoryReader,
    StorageContext,
    load_index_from_storage
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding
import pdfplumber  # reliable PDF extraction

load_dotenv()

INDEX_DIR = "storage"
_index_lock = Lock()
CHUNK_DOCS = 5
TOP_K_CHUNKS = 5

uploaded_file_chunks = []  # global to store last uploaded doc chunks


# ---------------------------
# Build or load RAG index
# ---------------------------
def build_index(file_path):
    with _index_lock:
        llm = Ollama(model="mistral", temperature=0, request_timeout=120)
        embed_model = OllamaEmbedding(model_name="nomic-embed-text")
        splitter = SentenceSplitter(chunk_size=300, chunk_overlap=30)

        Settings.llm = llm
        Settings.embed_model = embed_model
        Settings.node_parser = splitter

        documents = SimpleDirectoryReader(input_files=[file_path]).load_data()
        doc_queue = deque(documents)
        index = None

        while doc_queue:
            batch = [doc_queue.popleft() for _ in range(min(CHUNK_DOCS, len(doc_queue)))]
            if index is None:
                index = VectorStoreIndex.from_documents(batch)
            else:
                index.insert_documents(batch)

        index.storage_context.persist(persist_dir=INDEX_DIR)
        query_engine = index.as_query_engine(
            similarity_top_k=TOP_K_CHUNKS,
            response_mode="compact"
        )
        return query_engine


def load_index():
    if not os.path.exists(INDEX_DIR):
        return None
    try:
        storage_context = StorageContext.from_defaults(persist_dir=INDEX_DIR)
        index = load_index_from_storage(storage_context)
        query_engine = index.as_query_engine(
            similarity_top_k=TOP_K_CHUNKS,
            response_mode="compact"
        )
        return query_engine
    except Exception as e:
        print("Failed to load existing RAG index:", e)
        return None


# ---------------------------
# PDF to text and chunks
# ---------------------------
def parse_document_into_chunks(file_path, chunk_size=500, chunk_overlap=50):
    """Extract text from PDF and split into chunks."""
    global uploaded_file_chunks
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"Failed to extract text from {file_path}: {e}")
        return []

    if not text.strip():
        return []

    # Chunking
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append({"text": chunk_text, "category_score": 0})
        start += chunk_size - chunk_overlap

    uploaded_file_chunks = chunks
    return chunks


# ---------------------------
# Generate summary
# ---------------------------
def generate_summary_from_chunks(chunks):
    """Simple summary: take first 5 chunk snippets."""
    if not chunks:
        return "No text available to summarize."
    summary = " ".join([c["text"][:150] for c in chunks[:5]])
    return summary