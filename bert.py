# bert.py

import os
import torch

os.environ["TOKENIZERS_PARALLELISM"] = "false"
torch.set_num_threads(1)

import multiprocessing as mp
mp.set_start_method("spawn", force=True)

from transformers import pipeline
import numpy as np
import logging

# ------------------------------
# Load model once
# ------------------------------

classifier = pipeline(
    "zero-shot-classification",
    model="facebook/bart-large-mnli",
    device=-1,
    framework="pt"
)

# Legal labels (tune as needed)
LABELS = [
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
# Chunking helper
# ------------------------------

def chunk_text(text, max_words=200):
    words = text.split()
    chunks = []

    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i:i + max_words])
        if len(chunk.strip()) > 50:
            chunks.append(chunk)

    return chunks


# ------------------------------
# Main classifier
# ------------------------------

def classify_document(text):

    try:
        chunks = chunk_text(text)

        if not chunks:
            return {
                "top_predictions": [("Unknown", 0)],
                "reasoning": "No valid text chunks."
            }

        label_scores = {label: [] for label in LABELS}

        # ------------------------------
        # Run classification per chunk
        # ------------------------------

        for chunk in chunks[:15]:  # 🚨 limit for speed

            with torch.no_grad():
                result = classifier(chunk, LABELS)

            for label, score in zip(result["labels"], result["scores"]):
                label_scores[label].append(score)

        # ------------------------------
        # Aggregate scores (MEAN + SUPPORT)
        # ------------------------------

        aggregated = {}

        for label, scores in label_scores.items():

            if not scores:
                continue

            mean_score = np.mean(scores)
            support = len(scores) / len(chunks)

            # Weighted score
            final_score = mean_score * (0.7 + 0.3 * support)

            aggregated[label] = float(final_score)

        # ------------------------------
        # Sort predictions
        # ------------------------------

        sorted_preds = sorted(
            aggregated.items(),
            key=lambda x: x[1],
            reverse=True
        )

        top_label, top_score = sorted_preds[0]

        # ------------------------------
        # Confidence calibration
        # ------------------------------

        if top_score < 0.4:
            top_label = "Unknown"

        # ------------------------------
        # Reasoning
        # ------------------------------

        top_chunks = []

        for chunk in chunks[:5]:
            if top_label.lower() in chunk.lower():
                top_chunks.append(chunk[:120])

        reasoning = f"Top label '{top_label}' based on {len(chunks)} chunks."

        if top_chunks:
            reasoning += " Evidence: " + " | ".join(top_chunks[:2])

        return {
            "top_predictions": sorted_preds[:3],
            "reasoning": reasoning
        }

    except Exception as e:
        logging.error(f"BERT classification failed: {e}")

        return {
            "top_predictions": [("Unknown", 0)],
            "reasoning": "Classifier failed."
        }
    
def classify_with_bert(text):
    """
    Wrapper to match app.py expectations.
    Returns: (label, confidence)
    """

    result = classify_document(text)

    try:
        top_preds = result.get("top_predictions", [])

        if not top_preds:
            return "Unknown", 0

        label, score = top_preds[0]

        return label, float(score)

    except Exception as e:
        logging.error(f"BERT wrapper failed: {e}")
        return "Unknown", 0