from flask import Flask, request, jsonify
import json
import os
from werkzeug.security import generate_password_hash, check_password_hash

from embedding import embed_and_store   # ← imports from embedding.py in same dir

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), 'db.json')

def load_db():
    if not os.path.exists(DB_PATH):
        return {"users": []}
    with open(DB_PATH, 'r') as f:
        return json.load(f)

def save_db(data):
    with open(DB_PATH, 'w') as f:
        json.dump(data, f, indent=2)

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    
    db = load_db()
    
    if any(u['username'] == username for u in db['users']):
        return jsonify({"error": "User already exists"}), 409
    
    db['users'].append({
        "username": username,
        "password": generate_password_hash(password)
    })
    save_db(db)
    
    return jsonify({"message": "Account created"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    
    db = load_db()
    user = next((u for u in db['users'] if u['username'] == username), None)
    
    if not user or not check_password_hash(user['password'], password):
        return jsonify({"error": "Invalid credentials"}), 401
    
    return jsonify({"message": "Login successful"}), 200

@app.route('/embed-files', methods=['POST'])
def embed_files():
    data = request.get_json()

    if not data or 'files' not in data:
        return jsonify({"error": "'files' field is required"}), 400

    file_paths = data['files']

    if not isinstance(file_paths, list) or len(file_paths) == 0:
        return jsonify({"error": "'files' must be a non-empty list of file paths"}), 400

    try:
        embed_and_store(file_paths)
        return jsonify({
            "message": f"Successfully embedded and stored {len(file_paths)} file(s)",
            "files": file_paths
        }), 200

    except FileNotFoundError as e:
        return jsonify({"error": f"File not found: {str(e)}"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)