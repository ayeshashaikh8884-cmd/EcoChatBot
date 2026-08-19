"""
Waste Management Chatbot - Flask backend
Model: llama3.2:latest (served locally via Ollama - https://ollama.com)

Structure:
    session3/app.py
    session3/data.json          -> waste management knowledge base
    session3/db.sqlite          -> stores chat history per session (memory)
    session3/templates/index.html

Run:
    1. Make sure Ollama is installed and running: `ollama serve`
    2. Pull the model once:                       `ollama pull llama3.2:latest`
    3. Install Flask:                              `pip install flask`
    4. Start the app:                              `python app.py`
    5. Open http://127.0.0.1:5000 in your browser
"""

from flask import Flask, render_template, request, jsonify, session
import sqlite3
import json
import os
import uuid
import urllib.request
import urllib.error

app = Flask(__name__)
app.secret_key = "waste-management-chatbot-secret-key"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "db.sqlite")
DATA_PATH = os.path.join(BASE_DIR, "data.json")

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "llama3.2:latest"

HISTORY_LIMIT = 20  # number of past messages to feed back in as "memory"


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def get_session_id():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return session["session_id"]


def save_message(session_id, role, message):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO conversations (session_id, role, message) VALUES (?, ?, ?)",
        (session_id, role, message),
    )
    conn.commit()
    conn.close()


def get_history(session_id, limit=HISTORY_LIMIT):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT role, message FROM conversations
        WHERE session_id = ?
        ORDER BY id ASC
        LIMIT ?
        """,
        (session_id, limit),
    )
    rows = cur.fetchall()
    conn.close()
    return [{"role": role, "content": message} for role, message in rows]


# ---------------------------------------------------------------------------
# Knowledge base + LLM helpers
# ---------------------------------------------------------------------------
def load_waste_data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_system_prompt():
    waste_data = load_waste_data()
    knowledge = json.dumps(waste_data, indent=2)
    return (
        "You are EcoBot, a friendly waste management assistant. "
        "You help users understand different types of waste, whether they are "
        "recyclable, how to recycle or dispose of them properly, and you give "
        "practical recommendations and suggestions to reduce waste.\n\n"
        "Reference knowledge base (waste type, description, recyclability, "
        "recycle details, recommendations, suggestions):\n"
        f"{knowledge}\n\n"
        "Guidelines:\n"
        "- Ground your answers in the knowledge base above when the topic matches.\n"
        "- For each waste item discussed, try to naturally cover: what it is (description), "
        "its type, whether/how it can be recycled (recycle details), and a recommendation "
        "or suggestion.\n"
        "- Keep answers concise, clear, and friendly.\n"
        "- If asked about something outside the knowledge base, use your general "
        "knowledge but stay focused on waste management, sustainability, and recycling.\n"
        "- If the question is completely unrelated to waste management, politely "
        "steer the conversation back to the topic."
    )


def call_ollama(messages):
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL, data=data, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("message", {}).get("content", "").strip()
    except urllib.error.URLError as e:
        return (
            "I couldn't reach the local AI model. Please make sure Ollama is "
            f"running (`ollama serve`) and that '{MODEL_NAME}' has been pulled "
            f"(`ollama pull {MODEL_NAME}`). Details: {e}"
        )
    except Exception as e:  # noqa: BLE001
        return f"Something went wrong while generating a response: {e}"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    waste_data = load_waste_data()
    return render_template("index.html", waste_data=waste_data)


@app.route("/chat", methods=["POST"])
def chat():
    payload = request.get_json(silent=True) or {}
    user_message = (payload.get("message") or "").strip()

    if not user_message:
        return jsonify({"reply": "Please type a message about waste management."})

    session_id = get_session_id()
    save_message(session_id, "user", user_message)

    # "memory" = prior turns for this session pulled from SQLite
    history = get_history(session_id)
    messages = [{"role": "system", "content": build_system_prompt()}] + history

    reply = call_ollama(messages)
    save_message(session_id, "assistant", reply)

    return jsonify({"reply": reply})


@app.route("/reset", methods=["POST"])
def reset():
    """Clears this session's chat memory."""
    session_id = get_session_id()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "cleared"})


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)