# users.py
from flask import Blueprint, request, jsonify
from database import get_conn
from auth import hash_password, verify_password, create_token

users = Blueprint("users", __name__)

@users.post("/register")
def register():
    data = request.json
    email = data["email"]
    password = data["password"]

    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO users (email, password_hash)
            VALUES (?, ?)
        """, (email, hash_password(password)))
        conn.commit()
    except:
        return jsonify({"error": "Email already exists"}), 400

    return jsonify({"message": "Registration successful"})

@users.post("/login")
def login():
    data = request.json
    email = data["email"]
    password = data["password"]

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id, password_hash FROM users WHERE email=?", (email,))
    user = cur.fetchone()

    if not user or not verify_password(password, user["password_hash"]):
        return jsonify({"error": "Invalid email or password"}), 401

    token = create_token(user["id"])
    return jsonify({"token": token})