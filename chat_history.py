from flask import Blueprint, request, jsonify
from database import get_conn
from auth import auth_required

history_bp = Blueprint("history", __name__)

# =======================================================
#  CREATE NEW CONVERSATION
# =======================================================
def create_new_conversation(user_id, title="New Conversation"):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO conversations (user_id, title)
        VALUES (?, ?)
    """, (user_id, title))

    conv_id = cur.lastrowid
    conn.commit()
    conn.close()
    return conv_id


# =======================================================
#  SAVE MESSAGE
# =======================================================
def save_message(conversation_id, user_id, sender, message):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO messages (conversation_id, user_id, sender, message)
        VALUES (?, ?, ?, ?)
    """, (conversation_id, user_id, sender, message))

    conn.commit()
    conn.close()
    return True


# =======================================================
#  UPDATE TITLE (OPTIONAL)
# =======================================================
def update_conversation_title(conversation_id, user_id, title):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        UPDATE conversations
        SET title=?
        WHERE id=? AND user_id=?
    """, (title, conversation_id, user_id))

    conn.commit()
    conn.close()


# =======================================================
#  GET USER'S CONVERSATIONS
# =======================================================
@history_bp.get("/conversations")
@auth_required
def get_user_conversations():

    conn = get_conn()
    conn.row_factory = dict_factory
    cur = conn.cursor()

    cur.execute("""
        SELECT id, title, created_at
        FROM conversations
        WHERE user_id=?
        ORDER BY created_at DESC
    """, (request.user_id,))

    rows = cur.fetchall()
    conn.close()

    return jsonify(rows)


# Convert SQLite rows → dict
def dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


# =======================================================
#  GET MESSAGES IN A CONVERSATION
# =======================================================
@history_bp.get("/conversation/<int:conv_id>")
@auth_required
def get_conversation_messages(conv_id):

    conn = get_conn()
    conn.row_factory = dict_factory
    cur = conn.cursor()

    # Check ownership
    cur.execute("""
        SELECT id FROM conversations
        WHERE id=? AND user_id=?
    """, (conv_id, request.user_id))

    if not cur.fetchone():
        conn.close()
        return jsonify({"error": "Forbidden"}), 403

    cur.execute("""
        SELECT sender, message, created_at
        FROM messages
        WHERE conversation_id=? AND user_id=?
        ORDER BY created_at ASC
    """, (conv_id, request.user_id))

    rows = cur.fetchall()
    conn.close()

    return jsonify(rows)