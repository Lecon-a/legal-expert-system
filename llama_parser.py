# llama_parser.py
import os
import asyncio
import json
from collections import defaultdict
from llama_parse import LlamaParse
from llama_index.llms.ollama import Ollama
from dotenv import load_dotenv
from prolog_engine import classify_with_prolog  # fallback

load_dotenv()

# Initialize parser & LLM
parser = LlamaParse(
    api_key=os.getenv("LLAMA_CLOUD_API_KEY"),
    result_type="markdown",
    parsing_instruction="Extract all readable legal text from the document."
)

llm = Ollama(model="mistral", temperature=0)

CATEGORIES = [
    "Contract",
    "Non-Disclosure Agreement",
    "Loan Agreement",
    "Rental Agreement",
    "Employment Agreement",
    "Partnership Agreement",
    "Service Agreement",
    "Lease Agreement",
    "Sales Agreement",
    "Memorandum of Understanding",
    "Legal Notice",
    "Statute / Law",
    "Court Filing",
    "Other"
]


# ---------------------------
# Async parser to avoid Flask blocking
# ---------------------------
async def parse_document(filepath):
    documents = await parser.aload_data(filepath)
    return documents


# ---------------------------
# Chunking helper
# ---------------------------
def chunk_text(text, chunk_size=3000, overlap=500):
    words = text.split()
    i = 0
    while i < len(words):
        yield " ".join(words[i:i + chunk_size])
        i += chunk_size - overlap


# ---------------------------
# Main classification function
# ---------------------------
def classify_document_with_llamaparse(filepath, timeout_per_chunk=20):
    """
    Chunked LlamaParse classification with weighted aggregation
    and Prolog fallback if majority unknown.
    """
    try:
        # 1️⃣ Parse document async
        documents = asyncio.run(parse_document(filepath))
        full_text = "\n".join([doc.text for doc in documents])
        chunked_texts = list(chunk_text(full_text))
        if not chunked_texts:
            return "Unknown", 0, "No text extracted from document."

        chunk_results = []

        # 2️⃣ Classify each chunk via LLM
        for chunk in chunked_texts:
            prompt = f"""
You are a highly accurate legal document classifier.
Classify the text below into ONE category from the list:

{', '.join(CATEGORIES)}

Instructions:
- Return ONLY valid JSON: {{"label": "...", "confidence": 0.0-1.0, "reasoning": "..."}}
- If unsure, guess the most probable category instead of "Unknown".
- Include reasoning for your choice.

Document chunk:
{chunk}
"""
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                future = loop.run_in_executor(None, llm.complete, prompt)
                response = future.result(timeout=timeout_per_chunk)
                data = json.loads(response.text.strip())
                chunk_results.append(data)
            except Exception as e:
                chunk_results.append({"label": "Unknown", "confidence": 0.5, "reasoning": str(e)})

        # 3️⃣ Aggregate results
        scores = defaultdict(float)
        for res in chunk_results:
            label = res.get("label", "Unknown")
            confidence = res.get("confidence", 0.5)
            scores[label] += confidence

        final_label = max(scores, key=scores.get)
        final_confidence = scores[final_label] / sum(scores.values())
        reasoning = f"Aggregated from {len(chunk_results)} chunks."

        # 4️⃣ Prolog fallback if too many unknowns
        unknown_count = sum(1 for res in chunk_results if res.get("label") == "Unknown")
        if unknown_count / len(chunk_results) > 0.7:
            try:
                final_label = classify_with_prolog(full_text)
                final_confidence = 0.8
                reasoning += " Used Prolog fallback due to many unknown chunks."
            except Exception as e:
                reasoning += f" Prolog fallback failed: {e}"

        return final_label, round(final_confidence, 2), reasoning

    except Exception as e:
        return "Unknown", 0, f"Classification failed entirely: {e}"