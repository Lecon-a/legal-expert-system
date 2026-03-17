import os
import logging
from flask import Flask, request, jsonify, render_template

from extractor import extract_text
from bert import classify_with_bert
from prolog_engine import classify_with_prolog
from llama_parser import classify_document_with_text
from rag_engine import build_index, query_rag

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

latest_text = ""
rag_index = None


# -----------------------------
# CLASSIFICATION PIPELINE
# -----------------------------
def classify_with_fallback(text):

    # 1️⃣ Try LLM classification (FAST, no LlamaParse)
    logging.info("Running LLM text classifier")
    label, confidence, reasoning = classify_document_with_text(text)

    if label != "Unknown" and confidence > 0.5:
        return label, confidence, reasoning

    # 2️⃣ Fallback → HuggingFace BERT
    logging.info("Running HuggingFace classifier")
    label, confidence = classify_with_bert(text)

    if confidence > 0.6:
        return label, confidence, "Predicted using BERT model"

    # 3️⃣ Final fallback → Prolog rules
    logging.info("Running Prolog classifier")
    label = classify_with_prolog(text)

    return label, 0.5, "Rule-based classification (Prolog)"


# -----------------------------
# ROUTES
# -----------------------------
@app.route("/")
def home():
    return render_template("chat.html")


@app.route("/upload", methods=["POST"])
def upload():

    global latest_text, rag_index

    if "document" not in request.files:
        return jsonify({"message": "No file uploaded"})

    file = request.files["document"]

    if file.filename == "":
        return jsonify({"message": "No file selected"})

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    logging.info(f"File uploaded: {filepath}")

    # -----------------------------
    # Extract text
    # -----------------------------
    latest_text = extract_text(filepath)
    logging.info(f"Extracted text length: {len(latest_text)}")

    if not latest_text or latest_text.startswith("Error"):
        return jsonify({
            "message": "Failed to extract text",
            "category": "Unknown",
            "confidence": 0,
            "reasoning": latest_text
        })

    # -----------------------------
    # Classification
    # -----------------------------
    label, confidence, reasoning = classify_with_fallback(latest_text)

    # -----------------------------
    # Build RAG index
    # -----------------------------
    logging.info("Building RAG index...")
    rag_index = build_index(filepath)

    return jsonify({
        "message": "Upload successful",
        "category": label,
        "confidence": confidence,
        "reasoning": reasoning
    })


@app.route("/ask", methods=["POST"])
def ask():

    global latest_text, rag_index

    question = request.form.get("question")

    if not question:
        return jsonify({"answer": "No question provided", "engine": "error"})

    if not latest_text:
        return jsonify({"answer": "Upload a document first", "engine": "error"})

    try:
        # -----------------------------
        # Use RAG if available
        # -----------------------------
        if rag_index:
            answer = query_rag(rag_index, question)
            return jsonify({"answer": answer, "engine": "RAG"})

        # -----------------------------
        # Fallback → direct LLM
        # -----------------------------
        prompt = f"""
Answer the question based on this document:

{latest_text[:4000]}

Question: {question}
"""

        answer = classify_document_with_text(prompt)[2]  # reuse LLM

        return jsonify({"answer": answer, "engine": "LLM"})

    except Exception as e:
        logging.error(f"Error in /ask: {e}")
        return jsonify({"answer": "Something went wrong", "engine": "error"})


# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)