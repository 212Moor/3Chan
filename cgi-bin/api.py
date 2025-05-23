#!/usr/bin/env python3
# -*- coding: utf-8 -*-     
import sqlite3
import json
import hashlib
import sys
import os
import urllib.parse
from os import path

DB_PATH = path.abspath(path.join(path.dirname(__file__), '../database.db'))

def print_headers():
    print("Content-Type: application/json; charset=utf-8")
    print("Access-Control-Allow-Origin: *")
    print()

def hash_password(password):
    salt = "3chan_salt_"
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()

def get_request_data():
    method = os.environ.get('REQUEST_METHOD', 'GET').upper()
    if method == 'POST':
        content_length = int(os.environ.get('CONTENT_LENGTH', 0))
        post_data = sys.stdin.read(content_length)
        return json.loads(post_data) if post_data else {}
    else:
        query = os.environ.get('QUERY_STRING', '')
        return dict(urllib.parse.parse_qsl(query))

def main():
    print_headers()
    data = get_request_data()
    action = data.get('action')

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    try:
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
                c.execute("""
                    INSERT INTO users (username, password_hash, avatar)
                    VALUES (?, ?, ?)
                """, (username, password_hash, 'default.png'))
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
            elif hash_password(password) != user["password_hash"]:
                print(json.dumps({"success": False, "error": "Mot de passe incorrect"}))
            else:
                print(json.dumps({
                    "success": True,
                    "user_id": user["id"],
                    "username": username,
                    "avatar": user["avatar"]
                }))

        elif action == 'send_message':
            user_id = data.get('user_id')
            content = data.get('content', '')
            recipient_id = data.get('recipient_id')  

            if not isinstance(content, str):
                raise ValueError("Message invalide (doit être une chaîne de caractères)")
            content = content.strip()
            parent_id = int(data.get('parent_id', 0))

            if not user_id:
                raise ValueError("L'ID utilisateur est requis")
            if not content:
                raise ValueError("Le message ne peut pas être vide")

            c.execute("""
                INSERT INTO messages (content, user_id, parent_id, recipient_id)
                VALUES (?, ?, ?, ?)
            """, (content, user_id, parent_id, recipient_id))
            conn.commit()
            print(json.dumps({"success": True}))

        elif action == 'get_users':
            c.execute("SELECT id, username FROM users")
            users = [dict(row) for row in c.fetchall()]
            print(json.dumps(users))


        elif action == 'get_messages':
            try:
                user_id = data.get('user_id')

                c.execute("""
                    SELECT m.id, m.content, m.parent_id, m.created_at, m.recipient_id,
                        u.username, u.avatar
                    FROM messages m
                    JOIN users u ON m.user_id = u.id
                    WHERE m.recipient_id IS NULL
                    OR m.user_id = ?
                    OR m.recipient_id = ?
                    ORDER BY m.created_at DESC
                """, (user_id, user_id))

                messages = []
                for row in c.fetchall():
                    if row['content'] is not None:
                        messages.append(dict(row))
                print(json.dumps(messages))
            except Exception as e:
                print(json.dumps({"success": False, "error": "Erreur lors du chargement des messages : " + str(e)}))

        elif action == 'delete_message':
            user_id = data.get('user_id')
            message_id = data.get('message_id')

            if not user_id or not message_id:
                raise ValueError("Paramètres manquants")
            c.execute("SELECT username FROM users WHERE id = ?", (user_id,))
            user = c.fetchone()
            if not user or user["username"].lower() != "admin":
                print(json.dumps({"success": False, "error": "Non autorisé"}))
            else:
                c.execute("DELETE FROM messages WHERE id = ?", (message_id,))
                conn.commit()
                print(json.dumps({"success": True}))


        
        elif action == 'update_avatar':
            user_id = data.get('user_id')
            avatar_data = data.get('avatar')
            if not avatar_data:
                raise ValueError("Données d'avatar manquantes")

            AVATAR_DIR = path.abspath(path.join(path.dirname(__file__), '../assets/avatars'))
            os.makedirs(AVATAR_DIR, exist_ok=True)
            filename = f"avatar_{user_id}.png"
            with open(path.join(AVATAR_DIR, filename), "wb") as f:
                f.write(bytes.fromhex(avatar_data))
            c.execute("UPDATE users SET avatar = ? WHERE id = ?", (filename, user_id))
            conn.commit()
            print(json.dumps({"success": True, "avatar": filename}))

        elif action == 'get_user':
            user_id = data.get('id')
            c.execute("SELECT id, username, avatar FROM users WHERE id = ?", (user_id,))
            user = c.fetchone()
            print(json.dumps(dict(user)))

        else:
            print(json.dumps({"success": False, "error": "Action inconnue"}))

    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
    finally:
        conn.close()

if __name__ == "__main__":
    main()
