python3 init_db.py #INITIALISE BDD

python3 -m http.server --cgi 'PORT'

sqlite3 database.db "SELECT * FROM users;" #VOIR UTILISATEURS

sqlite3 database.db "PRAGMA table_info(users);" #VOIR TABLE

http://localhost:8001/index.html
