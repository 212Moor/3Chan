python3 -m http.server --cgi 'PORT'
sqlite3 database.db "SELECT * FROM users;"
sqlite3 database.db "PRAGMA table_info(users);"