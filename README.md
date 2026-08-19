# EcoBot — Waste Management Chatbot

A memory-based waste management chatbot built with **Flask**, a local **Ollama (`llama3.2:latest`)** model, and **Bootstrap-only** styling on the frontend (no separate custom CSS/JS files).

EcoBot answers questions about waste types, whether they're recyclable, how to recycle/dispose of them properly, and gives recommendations and suggestions to reduce waste — and remembers the conversation within a session using SQLite.

---

## Project Structure

```
session3/
├── app.py                 # Flask backend + Ollama integration + SQLite memory
├── data.json               # Waste management knowledge base
├── db.sqlite                # Auto-created on first run — stores chat history (memory)
├── requirements.txt         # Python dependencies (Flask, gunicorn)
└── templates/
    └── index.html          # Bootstrap-only frontend with floating chatbot icon
```

---

## How It Works

| Piece | Role |
|---|---|
| **`app.py`** | Flask server. Serves the page, exposes `/chat` and `/reset` endpoints, loads `data.json` as context, calls Ollama's local API, and reads/writes chat history to `db.sqlite`. |
| **`data.json`** | Knowledge base of waste categories — each with `type`, `description`, `recyclable`, `recycle_details`, `recommendations`, and `suggestions` — injected into the model's system prompt. |
| **`db.sqlite`** | Stores every user/assistant message per browser session, so previous turns are replayed back to the model — giving EcoBot "memory" of the conversation. |
| **`templates/index.html`** | The webpage. Uses **only Bootstrap 5** (via CDN) for all layout/styling and interactions (navbar, cards, offcanvas chat panel). The only JavaScript included is the minimal code required to call the `/chat` API and render replies. |

---

## Prerequisites

1. **Python 3.9+**
2. **Ollama** installed and running locally → https://ollama.com/download
3. The `llama3.2:latest` model pulled locally
4. Dependencies from `requirements.txt`

---

## Local Setup & Run

### 1. Install Ollama and pull the model
```bash
ollama serve
ollama pull llama3.2:latest
```
Keep `ollama serve` running in the background — the Flask app calls it at `http://localhost:11434/api/chat`.

### 2. Set up the Python environment
```bash
cd session3
python -m venv venv
source venv/bin/activate      # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Run the Flask app
```bash
python app.py
```

### 4. Open the chatbot
Visit **http://127.0.0.1:5000** in your browser.

- Waste category info is shown as cards on the page.
- Click the round chat icon in the **bottom-right corner** to open the chat window (a Bootstrap `offcanvas` panel).
- Ask questions like:
  - "Is plastic recyclable?"
  - "How do I dispose of old batteries?"
  - "Give me tips to reduce food waste."
- Click **Clear chat** to wipe the session's memory in `db.sqlite` and start fresh.

---

## Key Endpoints

| Route | Method | Purpose |
|---|---|---|
| `/` | GET | Renders `index.html` with waste category cards populated from `data.json`. |
| `/chat` | POST | Accepts `{ "message": "..." }`, saves it to SQLite, sends the full conversation + knowledge base to `llama3.2:latest` via Ollama, saves and returns the reply. |
| `/reset` | POST | Deletes the current session's chat history from `db.sqlite`. |

---

## Customizing the Knowledge Base

Edit `data.json` to add or update waste categories. Each entry follows this shape:

```json
{
  "type": "Plastic",
  "description": "Short summary of the waste category.",
  "recyclable": true,
  "recycle_details": "How to sort/prepare/recycle this item.",
  "recommendations": "General advice to reduce or reuse this waste.",
  "suggestions": "A practical action the user can take."
}
```

The Flask app automatically loads and injects the entire file into the chatbot's system prompt, so updates take effect the next time the app restarts.

---

## Deploying to Render

Render's web service containers **cannot run Ollama** (no persistent local model daemon, no GPU on free/starter tiers). To deploy successfully, choose one of these approaches:

- **Option A — Remote Ollama:** Run Ollama yourself on a separate machine/VM with a publicly reachable (and secured) endpoint, and point `OLLAMA_URL` in `app.py` at it.
- **Option B — Hosted LLM API:** Replace the `call_ollama()` function in `app.py` with a call to a hosted LLM provider (Anthropic, OpenAI, Groq, Together, etc.) instead of a local Ollama instance.

### Render setup steps

1. Push this project to a GitHub repository.
2. On [Render](https://render.com), create a **New Web Service** and connect the repo.
3. Set the **Root Directory** to `session3` (if your repo has other folders at the root).
4. **Build Command:**
   ```
   pip install -r requirements.txt
   ```
5. **Start Command:**
   ```
   gunicorn app:app
   ```
   Render sets a `$PORT` environment variable automatically — Gunicorn reads it, so no code changes are needed for the port itself. (Keep `app.run(debug=True, port=5000)` inside the `if __name__ == "__main__":` block — it's only used for local runs.)
6. Add any required environment variables (e.g., `OLLAMA_URL`, or an API key if you switch to a hosted LLM provider) under **Environment** in the Render dashboard.
7. Deploy. Render will build and host the app; your live URL will serve the same chatbot experience as local `http://127.0.0.1:5000`.

> **Note:** `db.sqlite` on Render's free tier is stored on ephemeral disk — it will reset on redeploys/restarts. For persistent chat memory in production, use a Render Disk (paid) or switch to a managed database (e.g., Postgres).

---

## Notes on "Bootstrap-only, no internal CSS/JS"

- All layout, colors, spacing, buttons, cards, and the chat panel use **Bootstrap 5 utility and component classes only** — no custom stylesheet.
- The chat window's open/close behavior is handled by **Bootstrap's built-in `offcanvas` component**, not custom JavaScript.
- The only `<script>` block in `index.html` is the minimal logic needed to `fetch()` the `/chat` API and append messages to the chat window — unavoidable application logic, not styling.
- Bootstrap and Bootstrap Icons are loaded via CDN since there are no local static asset files in this project structure.

---

## Troubleshooting

| Issue | Fix |
|---|---|
| Chatbot replies with a connection error | Make sure `ollama serve` is running and `llama3.2:latest` has been pulled (for local use), or that `OLLAMA_URL` points to a reachable endpoint (for hosted use). |
| Chat doesn't remember earlier questions | Check that `db.sqlite` is writable and that cookies are enabled in your browser (the session ID is stored in a cookie). |
| Cards on the page are empty | Confirm `data.json` is valid JSON and located in the same folder as `app.py`. |
| Chat icon doesn't open the panel | Confirm the Bootstrap Bundle JS `<script>` tag loaded successfully (check browser console/network tab). |
| App fails to start on Render | Confirm the Start Command is `gunicorn app:app` and `requirements.txt` includes `gunicorn`. |
