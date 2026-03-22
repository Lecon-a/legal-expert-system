import time
import logging
from dotenv import load_dotenv

from llama_index.core import VectorStoreIndex, Document
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama

load_dotenv()

# ============================================================
# MODELS
# ============================================================

EMBED_MODEL = OllamaEmbedding(model_name="nomic-embed-text")

LLM = Ollama(
    model="llama3",
    request_timeout=120.0
)


# ============================================================
# CHUNKING
# ============================================================

def parse_document_into_chunks(text, chunk_size=250, overlap=40):
    """
    Convert long text into overlapping chunks for RAG.
    """
    try:
        words = text.split()
        chunks = []

        step = chunk_size - overlap

        for i in range(0, len(words), step):
            chunk = " ".join(words[i:i + chunk_size])

            if len(chunk.strip()) > 80:  # ignore tiny chunks
                chunks.append(chunk)

        # Hard cap to prevent overloading vector index
        if len(chunks) > 100:
            chunks = chunks[:100]

        logging.info(f"Chunks created: {len(chunks)}")
        return chunks

    except Exception as e:
        logging.error(f"Chunk parsing failed: {e}")
        return []


# ============================================================
# BUILD RAG INDEX
# ============================================================

def build_index(text):
    """
    Turns extracted text → chunked docs → vector index → query engine.
    """
    try:
        chunks = parse_document_into_chunks(text)

        if not chunks:
            raise ValueError("No chunks generated")

        documents = [Document(text=chunk) for chunk in chunks]

        index = VectorStoreIndex.from_documents(
            documents,
            embed_model=EMBED_MODEL
        )

        query_engine = index.as_query_engine(
            llm=LLM,
            similarity_top_k=2
        )

        return query_engine

    except Exception as e:
        logging.error(f"Index build failed: {e}")
        return None


# ============================================================
# 🔥 LEGAL DOCUMENT CLASSIFIER USING RAG
# ============================================================

def classify_legal_document(text):

    try:
        prompt = f"""
You are a legal document classifier.

Your job:
Determine if the document is a LEGAL document.

Legal documents include:
- contracts
- agreements
- NDAs
- policies
- laws
- court judgments
- legal notices

Respond STRICTLY in this format:

ANSWER: YES or NO
REASON: short explanation

Document:
{text[:2000]}
"""

        response = LLM.complete(prompt)
        output = response.text.strip()

        # Normalize
        output_upper = output.upper()

        if "ANSWER: YES" in output_upper:
            return True, output

        return False, output

    except Exception as e:
        logging.error(f"Legal classification failed: {e}")
        return False, "Classification failed"
    
    
# ============================================================
# QUERY RAG (Strict IRAC Legal Reasoning)
# ============================================================

def query_rag(query_engine, question):
    """
    Main legal reasoning engine: uses IRAC format.
    """
    try:
        start = time.time()

        prompt = f"""
        You are a strict legal reasoning assistant.
        ONLY use the provided document context.
        DO NOT invent any laws, facts, or clauses.

        If the answer is not found, say:
        "Not explicitly stated in the document."

        Follow IRAC format:

        ISSUE:
        - Identify the legal issue.

        RULE:
        - Cite any relevant clause or principle *from the document only*.

        APPLICATION:
        - Apply rules to the question strictly based on the document.

        CONCLUSION:
        - Provide the concise legal answer.

        Question:
        {question}
        """

        response = query_engine.query(prompt)

        elapsed = time.time() - start
        logging.info(f"RAG response time: {elapsed:.2f}s")

        answer = getattr(response, "response", str(response)).strip()

        # Extract sources (optional)
        sources = []
        if hasattr(response, "source_nodes"):
            for node in response.source_nodes[:2]:
                text = node.text.strip().replace("\n", " ")
                sources.append(text[:180])

        return {
            "answer": answer,
            "sources": sources
        }

    except Exception as e:
        logging.error(f"RAG query failed: {e}")
        return {
            "answer": "⚠️ Failed to retrieve answer.",
            "sources": []
        }