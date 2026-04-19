"""
main.py
-------
Flask server exposing:
  POST /signup
  POST /login
  POST /embed-files   — upload files (multipart) or pass absolute server paths (JSON)
  POST /search        — semantic search over embedded files
"""

from flask import Flask, request, jsonify
import json
import os
import tempfile
from pathlib import Path
from werkzeug.security import generate_password_hash, check_password_hash

from embedding import embed_and_store
from search import search_similar

app = Flask(__name__)

# Files are streamed to disk before processing so this is a disk-space
# limit, not a RAM limit. Raise or remove as needed.
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024   # 500MB

DB_PATH = os.path.join(os.path.dirname(__file__), 'db.json')


def load_db():
    if not os.path.exists(DB_PATH):
        return {"users": []}
    with open(DB_PATH, 'r') as f:
        return json.load(f)


def save_db(data):
    with open(DB_PATH, 'w') as f:
        json.dump(data, f, indent=2)


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.route('/signup', methods=['POST'])
def signup():
    data     = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    db = load_db()
    if any(u['username'] == username for u in db['users']):
        return jsonify({"error": "User already exists"}), 409

    db['users'].append({
        "username": username,
        "password": generate_password_hash(password),
    })
    save_db(db)
    return jsonify({"message": "Account created"}), 201


@app.route('/login', methods=['POST'])
def login():
    data     = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    db   = load_db()
    user = next((u for u in db['users'] if u['username'] == username), None)

    if not user or not check_password_hash(user['password'], password):
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify({"message": "Login successful"}), 200


# ── Embed Files ───────────────────────────────────────────────────────────────

@app.route('/embed-files', methods=['POST'])
def embed_files():
    """
    Two ways to call this:

    1. Multipart upload (Postman / frontend / curl):
       Send files as form-data under the key 'files'.
       Files are saved to a temp directory, embedded, then deleted.
       Supports PDFs and plain text files.

       curl example:
         curl -X POST http://localhost:5000/embed-files \
           -F "files=@/path/to/Lab3Notes.pdf" \
           -F "files=@/path/to/notes.txt"

    2. JSON absolute paths (local scripting / dev):
       { "files": ["/absolute/path/to/file.pdf", ...] }
    """

    # ── Multipart upload ──────────────────────────────────────────────────────
    if request.files:
        uploads = request.files.getlist('files')
        if not uploads or all(u.filename == '' for u in uploads):
            return jsonify({"error": "No files received under the 'files' key"}), 400

        tmp_dir     = tempfile.mkdtemp(prefix="embed_")
        saved_paths = []

        try:
            for upload in uploads:
                dest = Path(tmp_dir) / upload.filename
                upload.save(str(dest))
                saved_paths.append(str(dest))

            result = embed_and_store(saved_paths)
            return jsonify({
                "message": f"Processed {result['stored']} file(s)",
                "stored":  result["stored"],
                "skipped": result["skipped"],
            }), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500

        finally:
            for p in saved_paths:
                try:
                    os.remove(p)
                except OSError:
                    pass
            try:
                os.rmdir(tmp_dir)
            except OSError:
                pass

    # ── JSON absolute paths ───────────────────────────────────────────────────
    data = request.get_json(silent=True)
    if data and 'files' in data:
        file_paths = data['files']
        if not isinstance(file_paths, list) or not file_paths:
            return jsonify({"error": "'files' must be a non-empty list of paths"}), 400

        try:
            result = embed_and_store(file_paths)
            return jsonify({
                "message": f"Processed {result['stored']} file(s)",
                "stored":  result["stored"],
                "skipped": result["skipped"],
            }), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return jsonify({
        "error": (
            "Send files as multipart/form-data under the 'files' key, "
            "or a JSON body with a 'files' list of absolute server paths."
        )
    }), 400


# ── Search ────────────────────────────────────────────────────────────────────

@app.route('/search', methods=['POST'])
def search():
    """
    Semantic search over embedded files.

    Request body:
      { "query": "your search string", "n_results": 3 }

    Response:
      {
        "query": "...",
        "results": [
          { "filename": "...", "source": "...", "distance": 0.12, "text": "..." },
          ...
        ]
      }
    """
    data = request.get_json()

    if not data or 'query' not in data:
        return jsonify({"error": "'query' field is required"}), 400

    query_text = data['query']
    n_results  = data.get('n_results', 3)

    if not isinstance(query_text, str) or not query_text.strip():
        return jsonify({"error": "'query' must be a non-empty string"}), 400

    try:
        hits = search_similar(query_text, n_results=n_results)
        return jsonify({"query": query_text, "results": hits}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)