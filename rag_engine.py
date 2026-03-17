# rag_engine.py
import os
import logging
from dotenv import load_dotenv
from llama_parse import LlamaParse
from llama_index.core import VectorStoreIndex, Document
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama

load_dotenv()
# ------------------------------
# CONFIG
# ------------------------------

PARSER = LlamaParse(
    api_key=os.getenv("LLAMA_CLOUD_API_KEY"),
    result_type="markdown", 
    verbose=False
)

EMBED_MODEL = OllamaEmbedding(model_name="nomic-embed-text")

LLM = Ollama(model="llama3", request_timeout=60.0)


# ------------------------------
# CHUNKING (FIXED)
# ------------------------------

def parse_document_into_chunks(file_path):

    try:
        documents = PARSER.load_data(file_path)

        if not documents:
            return []

        full_text = "\n".join([doc.text for doc in documents])

        # Simple chunking
        words = full_text.split()
        chunks = []

        chunk_size = 300
        overlap = 50

        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i:i + chunk_size])

            if len(chunk.strip()) > 50:
                chunks.append(chunk)

        # ✅ 🔥 ADD IT HERE (RIGHT BEFORE RETURN)
        if len(chunks) > 120:
            chunks = chunks[:120]

        return chunks

    except Exception as e:
        logging.error(f"Chunk parsing failed: {e}")
        return []


# ------------------------------
# BUILD INDEX
# ------------------------------

def build_index(file_path):

    try:
        chunks = parse_document_into_chunks(file_path)

        if not chunks:
            raise ValueError("No chunks generated")

        documents = [Document(text=chunk) for chunk in chunks]

        index = VectorStoreIndex.from_documents(
            documents,
            embed_model=EMBED_MODEL
        )

        query_engine = index.as_query_engine(
            llm=LLM,
            similarity_top_k=4
        )

        return query_engine

    except Exception as e:
        logging.error(f"Index build failed: {e}")
        raise


# ------------------------------
# SUMMARY
# ------------------------------

def generate_summary_from_chunks(chunks):

    try:
        if not chunks:
            return "No content to summarize."

        text = "\n".join(chunks[:10])  # limit

        prompt = f"""
Summarize this legal document clearly:

{text}
"""

        response = LLM.complete(prompt)

        return response.text.strip()

    except Exception as e:
        logging.error(f"Summary failed: {e}")
        return "Summary generation failed."
    

def query_rag(query_engine, question):
    """
    Query the RAG engine safely.
    """

    try:
        response = query_engine.query(question)

        # LlamaIndex responses can be objects
        if hasattr(response, "response"):
            return response.response

        return str(response)

    except Exception as e:
        logging.error(f"RAG query failed: {e}")
        return "Failed to retrieve answer from document."