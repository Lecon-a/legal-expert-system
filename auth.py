from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_conn

auth_bp = Blueprint("auth", __name__)


# ---------------------------
# HELPER: auth_required
# ---------------------------
def auth_required(route_func):
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized"}), 401
        return route_func(*args, **kwargs)
    wrapper.__name__ = route_func.__name__
    return wrapper


# ---------------------------
# REGISTER
# ---------------------------
@auth_bp.post("/register")
def register():
    data = request.json
    fullname = data.get("fullname")
    email = data.get("email")
    password = data.get("password")

    print(f"Registering: {fullname}, {email}")

    if not all([fullname, email, password]):
        return jsonify({"error": "Missing fields"}), 400

    conn = get_conn()
    cur = conn.cursor()

    # check if email exists
    cur.execute("SELECT id FROM users WHERE email=?", (email,))
    if cur.fetchone():
        return jsonify({"error": "Email already registered"}), 400

    hashed = generate_password_hash(password)

    cur.execute("INSERT INTO users(fullname, email, password) VALUES (?, ?, ?)",
                (fullname, email, hashed))
    conn.commit()

    return jsonify({"success": True, "message": "Account created"})


# ---------------------------
# LOGIN
# ---------------------------
@auth_bp.post("/login")
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id, password FROM users WHERE email=?", (email,))
    row = cur.fetchone()

    if not row or not check_password_hash(row["password"], password):
        return jsonify({"error": "Invalid credentials"}), 401

    session["user_id"] = row["id"]

    return jsonify({"success": True, "message": "Logged in"})


# ---------------------------
# LOGOUT
# ---------------------------
@auth_bp.get("/logout")
def logout():
    session.clear()
    return jsonify({"success": True})