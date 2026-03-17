# llama_parser.py

import os
import asyncio
import logging
from dotenv import load_dotenv
from llama_parse import LlamaParse
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

LLM = Ollama(
    model="llama3",
    request_timeout=60.0
)

# ------------------------------
# LABELS
# ------------------------------

LEGAL_LABELS = [
    "contract",
    "nda",
    "loan agreement",
    "employment agreement",
    "privacy policy",
    "terms of service",
    "court judgment",
    "statute / law",
    "legal notice"
]

# ------------------------------
# MAIN FUNCTION
# ------------------------------

async def classify_document_with_llamaparse(file_path):

    try:
        # ------------------------------
        # Step 1: Parse document
        # ------------------------------

        timeout = 30 + min(60, os.path.getsize(file_path) / 100000)

        documents = await asyncio.wait_for(
            PARSER.aload_data(
                file_path,
                extra_info={"max_pages": 5}  # 🔥 key fix
            ),
            timeout=timeout
        )

        if not documents:
            return ("Unknown", 0, "No content parsed.")

        # Combine text
        full_text = "\n".join([doc.text for doc in documents])

        if len(full_text.strip()) < 100:
            return ("Unknown", 0, "Parsed text too short.")

        # ------------------------------
        # Step 2: Truncate (VERY important)
        # ------------------------------

        truncated_text = full_text[:4000]

        # ------------------------------
        # Step 3: Prompt (STRICT FORMAT)
        # ------------------------------

        prompt = f"""
You are a legal document classifier.

Classify the document into ONE of the following categories:
{", ".join(LEGAL_LABELS)}

Return ONLY in this format:
LABEL: <label>
CONFIDENCE: <0-1>
REASON: <short explanation>

Document:
{truncated_text}
"""

        # ------------------------------
        # Step 4: LLM call (with timeout)
        # ------------------------------

        response = await asyncio.wait_for(
            LLM.acomplete(prompt),
            timeout=30
        )

        output = response.text.strip()

        # ------------------------------
        # Step 5: Parse response safely
        # ------------------------------

        label = "Unknown"
        confidence = 0
        reasoning = "Parsing failed."

        for line in output.split("\n"):
            if line.startswith("LABEL:"):
                label = line.replace("LABEL:", "").strip()
            elif line.startswith("CONFIDENCE:"):
                try:
                    confidence = float(line.replace("CONFIDENCE:", "").strip())
                except:
                    confidence = 0
            elif line.startswith("REASON:"):
                reasoning = line.replace("REASON:", "").strip()

        # ------------------------------
        # Step 6: Validation
        # ------------------------------

        if label not in LEGAL_LABELS:
            label = "Unknown"

        confidence = max(0, min(confidence, 1))

        return (label, confidence, reasoning)

    except asyncio.TimeoutError:
        logging.error("LlamaParse timed out")
        return ("Unknown", 0, "Timeout during parsing/classification.")

    except Exception as e:
        logging.error(f"LlamaParse pipeline failed: {e}")
        return ("Unknown", 0, "LlamaParse failed.")
    
def classify_document_with_text(text):

    try:
        truncated_text = text[:4000]

        prompt = f"""
            You are a legal document classifier.

            Classify into ONE:
            contract, nda, loan agreement, employment agreement,
            privacy policy, terms of service, court judgment,
            statute / law, legal notice

            Return:
            LABEL: <label>
            CONFIDENCE: <0-1>
            REASON: <short explanation>

            Document:
            {truncated_text}
        """

        response = LLM.complete(prompt)
        output = response.text.strip()

        label = "Unknown"
        confidence = 0
        reasoning = "Parsing failed."

        for line in output.split("\n"):
            if line.startswith("LABEL:"):
                label = line.replace("LABEL:", "").strip()
            elif line.startswith("CONFIDENCE:"):
                try:
                    confidence = float(line.replace("CONFIDENCE:", "").strip())
                except:
                    confidence = 0
            elif line.startswith("REASON:"):
                reasoning = line.replace("REASON:", "").strip()

        return (label, confidence, reasoning)

    except Exception as e:
        logging.error(f"Llama text classification failed: {e}")
        return ("Unknown", 0, "LLM classification failed.")