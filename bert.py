import pdfplumber
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
from transformers import TextClassificationPipeline
from collections import defaultdict
import os
from dotenv import load_dotenv

load_dotenv()

os.environ["HF_TOKEN"] = os.getenv("HF_TOKEN")
# -----------------------------
# Models
# -----------------------------

# Zero-shot classifier
bart_classifier = pipeline(
    "zero-shot-classification",
    model="facebook/bart-large-mnli"
)

# Legal-BERT cross-check
legal_model_name = "nlpaueb/legal-bert-base-uncased"

legal_tokenizer = AutoTokenizer.from_pretrained(legal_model_name)
legal_model = AutoModelForSequenceClassification.from_pretrained(legal_model_name)

legal_classifier = TextClassificationPipeline(
    model=legal_model,
    tokenizer=legal_tokenizer
)

# -----------------------------
# Legal Categories
# -----------------------------

LABELS = [
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
    "Criminal Law",
    "Other"
]

# -----------------------------
# PDF TEXT EXTRACTION
# -----------------------------

def extract_text_from_pdf(path):

    text = ""

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    return text


# -----------------------------
# TEXT CHUNKING
# -----------------------------

def chunk_text(text, chunk_size=800, overlap=150):

    chunks = []

    start = 0

    while start < len(text):

        end = start + chunk_size

        chunk = text[start:end]

        chunks.append(chunk)

        start += chunk_size - overlap

    return chunks


# -----------------------------
# ZERO-SHOT CLASSIFICATION
# -----------------------------

def bart_classify(chunk):

    prompt = f"""
You are a legal expert.

Classify the following legal document text into the most relevant legal category.

Document:
{chunk}
"""

    result = bart_classifier(prompt, LABELS, multi_label=True)

    return dict(zip(result["labels"], result["scores"]))


# -----------------------------
# LEGAL-BERT CROSS-CHECK
# -----------------------------

def legalbert_check(chunk):

    try:

        result = legal_classifier(chunk[:512])[0]

        return {result["label"]: result["score"]}

    except Exception:

        return {}


# -----------------------------
# SCORE AGGREGATION
# -----------------------------

def aggregate_scores(chunk_scores):

    scores = defaultdict(float)

    for chunk in chunk_scores:

        for label, score in chunk.items():

            scores[label] += score

    return scores


# -----------------------------
# MAIN CLASSIFICATION FUNCTION
# -----------------------------

def classify_document(pdf_path):

    text = extract_text_from_pdf(pdf_path)

    chunks = chunk_text(text)

    all_chunk_scores = []

    for chunk in chunks:

        bart_scores = bart_classify(chunk)

        bert_scores = legalbert_check(chunk)

        merged_scores = defaultdict(float)

        # Merge BART scores
        for label, score in bart_scores.items():
            merged_scores[label] += score

        # Merge BERT scores
        for label, score in bert_scores.items():
            merged_scores[label] += score

        all_chunk_scores.append(merged_scores)

    final_scores = aggregate_scores(all_chunk_scores)

    sorted_scores = sorted(
        final_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )

    top3 = sorted_scores[:3]

    return {
        "top_predictions": top3,
        "chunks_processed": len(chunks),
        "reasoning": f"Classification aggregated from {len(chunks)} document chunks using BART and Legal-BERT."
    }


# -----------------------------
# RUN TEST
# -----------------------------

# if __name__ == "__main__":

#     pdf_path = "uploads/Criminal-Law-of-Lagos-State.pdf"

#     result = classify_document(pdf_path)

#     print("\nTop 3 Predictions:\n")

#     for label, score in result["top_predictions"]:
#         print(f"{label}: {round(score,4)}")

#     print("\nReasoning:", result["reasoning"])