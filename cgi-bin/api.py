#!/usr/bin/env python3
import sqlite3
import json
import hashlib
import sys
import os
from os import path

DB_PATH = path.abspath(path.join(path.dirname(__file__), '../database.db'))

def print_headers():
    print("Content-Type: application/json; charset=utf-8")
    print("Access-Control-Allow-Origin: *")
    print()

def hash_password(password):
    salt = "3chan_salt_"
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        avatar TEXT DEFAULT 'default.png',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        thread_id INTEGER DEFAULT 1,
        parent_id INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)
    conn.commit()
    conn.close()

def main():
    print_headers()
    try:
        method = os.environ.get('REQUEST_METHOD', 'GET').upper()

        if method == 'POST':
            content_length = int(os.environ.get('CONTENT_LENGTH', 0))
            post_data = sys.stdin.read(content_length)
            data = json.loads(post_data) if post_data else {}
            action = data.get('action')
        else:  
            import urllib.parse
            query = os.environ.get('QUERY_STRING', '')
            data = dict(urllib.parse.parse_qsl(query))
            action = data.get('action')

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        if action == 'register':
            username = data.get('username', '').strip()
            password = data.get('password', '')
            if not username or not password:
                raise ValueError("Nom d'utilisateur et mot de passe requis")
            c.execute("SELECT id FROM users WHERE username = ?", (username,))
            if c.fetchone():
                print(json.dumps({"success": False, "error": "Nom d'utilisateur déjà pris"}))
            else:
                password_hash = hash_password(password)
                c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", 
                         (username, password_hash))
                conn.commit()
                user_id = c.lastrowid
                print(json.dumps({
                    "success": True, 
                    "user_id": user_id, 
                    "username": username,
                    "avatar": "default.png"
                }))

        elif action == 'login':
            username = data.get('username', '').strip()
            password = data.get('password', '')
            c.execute("SELECT id, password_hash, avatar FROM users WHERE username = ?", (username,))
            user = c.fetchone()
            if not user:
                print(json.dumps({"success": False, "error": "Utilisateur non trouvé"}))
            else:
                if hash_password(password) == user['password_hash']:
                    print(json.dumps({
                        "success": True, 
                        "user_id": user['id'], 
                        "username": username,
                        "avatar": user['avatar']
                    }))
                else:
                    print(json.dumps({"success": False, "error": "Mot de passe incorrect"}))

        elif action == 'update_avatar':
            user_id = data.get('user_id')
            avatar_data = data.get('avatar')
            
            os.makedirs('../assets/avatars', exist_ok=True)
            filename = f"avatar_{user_id}.png"
            
            with open(f"../assets/avatars/{filename}", "wb") as f:
                f.write(bytes.fromhex(avatar_data))
            
            c.execute("UPDATE users SET avatar = ? WHERE id = ?", (filename, user_id))
            conn.commit()
            print(json.dumps({"success": True, "avatar": filename}))

        elif action == 'get_user':
            user_id = data.get('id')
            c.execute("SELECT id, username, avatar FROM users WHERE id = ?", (user_id,))
            user = c.fetchone()
            print(json.dumps(dict(user)))

        elif action == 'send_message':
            user_id = data.get('user_id')
            content = data.get('content', '').strip()
            if not content:
                raise ValueError("Le message ne peut pas être vide")
            c.execute("""
                INSERT INTO messages (content, user_id) 
                VALUES (?, ?)
            """, (content, user_id))
            conn.commit()
            print(json.dumps({"success": True}))

        elif action == 'get_messages':
            c.execute("""
                SELECT m.id, m.content, m.created_at, u.username, u.avatar
                FROM messages m
                JOIN users u ON m.user_id = u.id
                ORDER BY m.created_at ASC
            """)
            messages = [dict(row) for row in c.fetchall()]
            print(json.dumps(messages))

        else:
            print(json.dumps({"success": False, "error": "Action inconnue"}))

    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    init_db()
    main()