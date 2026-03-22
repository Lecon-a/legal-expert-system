import os
import logging
from flask import Flask, request, jsonify, render_template, session, redirect

# --- Core Modules ---
from extractor import extract_text
from rag_engine import build_index, query_rag, classify_legal_document

# --- Auth + History ---
from auth import auth_bp, auth_required
from chat_history import history_bp, save_message, create_new_conversation
from database import init_db

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "super-secret-key")

app.config.update({
    "SESSION_COOKIE_HTTPONLY": True,
    "SESSION_COOKIE_SAMESITE": "Strict",
    "SESSION_COOKIE_SECURE": False,
    "PERMANENT_SESSION_LIFETIME": 60 * 60 * 4,
})

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

latest_text = ""
rag_index = None
rag_cache = {}

app.register_blueprint(auth_bp)
app.register_blueprint(history_bp)


# ================= LANDING =================
@app.route("/")
def index():
    if "user_id" in session:
        return redirect("/dashboard")
    return render_template("index.html")


@app.route("/auth")
def auth_page():
    return render_template("auth.html")


@app.route("/dashboard")
@auth_required
def dashboard():
    return render_template("dashboard.html")


# ================= UPLOAD =================
@app.route("/upload", methods=["POST"])
@auth_required
def upload():

    global latest_text, rag_index, rag_cache

    file = request.files.get("document")

    if not file or file.filename == "":
        return jsonify({"success": False, "message": "No file selected"})

    path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(path)

    # Extract text
    latest_text = extract_text(path)

    if not latest_text:
        return jsonify({"success": False, "message": "Text extraction failed"})

    # 🔥 CLASSIFY FIRST
    is_legal, reasoning = classify_legal_document(latest_text)

    # 🔥 Backup heuristic (VERY IMPORTANT)
    keywords = ["agreement", "contract", "party", "clause", "terms", "law"]

    if not is_legal:
        if any(k in latest_text.lower() for k in keywords):
            is_legal = True
            reasoning += " (Accepted via keyword fallback)"

    if not is_legal:
        return jsonify({
            "success": False,
            "message": "❌ Only legal documents allowed",
            "reasoning": reasoning
        })

    # 🔥 BUILD INDEX AFTER VALIDATION
    rag_index = build_index(latest_text)
    rag_cache.clear()

    return jsonify({
        "success": True,
        "message": "Legal document accepted",
        "reasoning": reasoning
    })

# ================= ASK =================
@app.route("/ask", methods=["POST"])
@auth_required
def ask():

    global rag_index, rag_cache

    user_id = session["user_id"]
    question = request.form.get("question", "").strip()
    conv_id = request.form.get("conversation_id")

    if not question:
        return jsonify({"answer": "No question provided"})

    if not rag_index:
        return jsonify({"answer": "Upload document first"})

    if not conv_id:
        conv_id = create_new_conversation(user_id)

    save_message(conv_id, user_id, "user", question)

    if question in rag_cache:
        answer = rag_cache[question]
        save_message(conv_id, user_id, "assistant", answer)
        return jsonify({"answer": answer, "conversation_id": conv_id})

    result = query_rag(rag_index, question)
    answer = result.get("answer", "No answer")

    rag_cache[question] = answer
    save_message(conv_id, user_id, "assistant", answer)

    return jsonify({
        "answer": answer,
        "conversation_id": conv_id
    })


# ================= RUN =================
if __name__ == "__main__":
    init_db()
    app.run(debug=True, use_reloader=False)