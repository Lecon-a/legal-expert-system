# app.py
import os
import logging
import threading
import asyncio
import nest_asyncio
from flask import Flask, request, jsonify, render_template

from extractor import extract_text
from rag_engine import build_index, generate_summary_from_chunks, parse_document_into_chunks

from bert import classify_document as hf_classify_document
from llama_parser import classify_document_with_llamaparse
from prolog_engine import classify_with_prolog

nest_asyncio.apply()
logging.basicConfig(level=logging.INFO)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__, template_folder="templates")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ------------------------------
# GLOBAL STATE (cached)
# ------------------------------

ragReady = False
query_engine = None

latest_text = ""
latest_chunks = []
latest_classification = None


# ------------------------------
# Async helper
# ------------------------------

def classify_document_sync(file_path):
    try:
        return asyncio.run(classify_document_with_llamaparse(file_path))
    except Exception as e:
        logging.error(f"LlamaParse classification failed: {e}")
        return {"category": "Unknown", "confidence": 0, "reasoning": "Classification failed."}


# ------------------------------
# Home route
# ------------------------------

@app.route("/")
def home():
    return render_template("chat.html")


# ------------------------------
# CLASSIFICATION PIPELINE
# ------------------------------

def classify_with_fallback(text, filepath):

    # 1️⃣ HuggingFace (fastest + primary)
    try:
        logging.info("Running HuggingFace classifier")

        hf_result = hf_classify_document(text)
        top = hf_result["top_predictions"][0]

        return {
            "category": top[0],
            "confidence": float(top[1]),
            "reasoning": hf_result["reasoning"],
            "engine": "huggingface"
        }

    except Exception as e:
        logging.warning(f"HuggingFace failed: {e}")

    # 2️⃣ LlamaParse fallback
    try:
        logging.info("Running LlamaParse classifier")

        label, confidence, reasoning = classify_document_sync(filepath)

        return {
            "category": label,
            "confidence": confidence,
            "reasoning": reasoning,
            "engine": "llamaparse"
        }

    except Exception as e:
        logging.warning(f"LlamaParse failed: {e}")

    # 3️⃣ Prolog fallback
    try:
        logging.info("Running Prolog classifier")

        label = classify_with_prolog(text)

        return {
            "category": label,
            "confidence": 0.6,
            "reasoning": "Rule-based classification",
            "engine": "prolog"
        }

    except Exception as e:
        logging.warning(f"Prolog failed: {e}")

    return {
        "category": "Unknown",
        "confidence": 0,
        "reasoning": "All classifiers failed",
        "engine": "none"
    }


# ------------------------------
# Upload endpoint
# ------------------------------

@app.route("/upload", methods=["POST"])
def upload():

    global latest_text, latest_chunks, latest_classification
    global query_engine, ragReady

    if "document" not in request.files:
        return jsonify({"success": False, "message": "No file uploaded."}), 400

    file = request.files["document"]

    if file.filename == "":
        return jsonify({"success": False, "message": "No file selected."}), 400

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(filepath)

    logging.info(f"File uploaded: {filepath}")

    # ------------------------------
    # Extract text (ONLY ONCE)
    # ------------------------------

    try:
        latest_text = extract_text(filepath)
    except Exception as e:
        logging.error(f"Text extraction failed: {e}")
        latest_text = ""

    # ------------------------------
    # Chunk text (ONLY ONCE)
    # ------------------------------

    try:
        latest_chunks = parse_document_into_chunks(latest_text)
    except Exception as e:
        logging.error(f"Chunking failed: {e}")
        latest_chunks = []

    # ------------------------------
    # Classification
    # ------------------------------

    latest_classification = classify_with_fallback(latest_text, filepath)

    logging.info(f"Classification result: {latest_classification}")

    # ------------------------------
    # Build RAG in background
    # ------------------------------

    ragReady = False

    def build_rag():

        global query_engine, ragReady

        try:
            logging.info("Building RAG index...")

            query_engine = build_index(latest_chunks)

            ragReady = True

            logging.info("RAG index ready")

        except Exception as e:
            logging.error(f"RAG build failed: {e}")

    threading.Thread(target=build_rag, daemon=True).start()

    # ------------------------------
    # Response
    # ------------------------------

    return jsonify({
        "success": True,
        "message": "Document uploaded successfully.",
        "category": latest_classification["category"],
        "confidence": latest_classification["confidence"],
        "reasoning": latest_classification["reasoning"],
        "engine": latest_classification["engine"]
    })


# ------------------------------
# Summary endpoint
# ------------------------------

@app.route("/summary", methods=["POST"])
def summary():

    global latest_chunks, latest_classification

    if not latest_chunks:
        return jsonify({"success": False, "summary": None})

    summary_text = generate_summary_from_chunks(latest_chunks)

    return jsonify({
        "success": True,
        "summary": summary_text,
        "category": latest_classification["category"] if latest_classification else "Unknown"
    })


# ------------------------------
# Ask endpoint
# ------------------------------

@app.route("/ask", methods=["POST"])
def ask():

    question = request.form.get("question", "").strip()

    if not question:
        return jsonify({"answer": "No question provided.", "engine": "N/A"})

    if not ragReady:
        return jsonify({"answer": "RAG index still building.", "engine": "N/A"})

    try:
        response = query_engine.query(question)

        return jsonify({
            "answer": str(response),
            "engine": "RAG"
        })

    except Exception as e:
        logging.error(e)

        return jsonify({
            "answer": "Failed to generate answer.",
            "engine": "error"
        })


# ------------------------------
# Run
# ------------------------------

if __name__ == "__main__":
    app.run(debug=True)