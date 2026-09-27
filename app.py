"""
Guestbook backend for oulanl's portfolio (0l-l.github.io).

Endpoints:
  GET    /                -> health check
  GET    /messages        -> list guestbook messages (most recent first)
  POST   /messages        -> submit a new guestbook message
  DELETE /messages/<id>   -> remove a message (requires admin token)

Storage: messages are kept in a local JSON file (messages.json). This is
intentionally simple (no external database) since the assignment flagged
database setup as the most common source of friction. Note that Render's
free-tier disk is ephemeral, so messages may reset on redeploy/restart --
that's an acceptable tradeoff for this assignment.
"""

import json
import os
import time
import uuid
from pathlib import Path

from flask import Flask, jsonify, request

app = Flask(__name__)


@app.after_request
def add_cors_headers(response):
    # Guestbook data is public/non-sensitive, so any origin may read/write it.
    # (For anything sensitive you'd restrict this to your GitHub Pages origin.)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Admin-Token"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
    return response


@app.route("/messages", methods=["OPTIONS"])
@app.route("/messages/<message_id>", methods=["OPTIONS"])
def cors_preflight(message_id=None):
    # Browsers send an OPTIONS preflight before POST/DELETE with custom headers.
    return jsonify({}), 204

DATA_FILE = Path(__file__).parent / "messages.json"
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN")  # set as a secret env var on Render

MAX_NAME_LEN = 60
MAX_MESSAGE_LEN = 500
MAX_STORED_MESSAGES = 200


def load_messages():
    if not DATA_FILE.exists():
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_messages(messages):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "guestbook-backend"})


@app.route("/messages", methods=["GET"])
def get_messages():
    messages = load_messages()
    # most recent first
    messages_sorted = sorted(messages, key=lambda m: m["created_at"], reverse=True)
    return jsonify({"count": len(messages_sorted), "messages": messages_sorted})


@app.route("/messages", methods=["POST"])
def post_message():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON."}), 400

    name = str(data.get("name", "")).strip()
    message = str(data.get("message", "")).strip()

    if not name:
        return jsonify({"error": "Name is required."}), 400
    if not message:
        return jsonify({"error": "Message is required."}), 400
    if len(name) > MAX_NAME_LEN:
        return jsonify({"error": f"Name must be {MAX_NAME_LEN} characters or fewer."}), 400
    if len(message) > MAX_MESSAGE_LEN:
        return jsonify({"error": f"Message must be {MAX_MESSAGE_LEN} characters or fewer."}), 400

    messages = load_messages()

    entry = {
        "id": uuid.uuid4().hex[:12],
        "name": name,
        "message": message,
        "created_at": time.time(),
    }
    messages.append(entry)

    # keep the file from growing unbounded
    if len(messages) > MAX_STORED_MESSAGES:
        messages = sorted(messages, key=lambda m: m["created_at"], reverse=True)[:MAX_STORED_MESSAGES]

    save_messages(messages)

    return jsonify({"status": "ok", "entry": entry}), 201


@app.route("/messages/<message_id>", methods=["DELETE"])
def delete_message(message_id):
    # Simple moderation auth: caller must send the correct admin token.
    # This demonstrates handling a secret via an environment variable --
    # the token is never stored in the repo.
    if not ADMIN_TOKEN:
        return jsonify({"error": "Admin moderation is not configured on this server."}), 503

    provided = request.headers.get("X-Admin-Token", "")
    if provided != ADMIN_TOKEN:
        return jsonify({"error": "Unauthorized."}), 401

    messages = load_messages()
    remaining = [m for m in messages if m["id"] != message_id]

    if len(remaining) == len(messages):
        return jsonify({"error": "Message not found."}), 404

    save_messages(remaining)
    return jsonify({"status": "deleted", "id": message_id})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
