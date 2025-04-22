import sqlite3

# Cria o banco e a tabela
def init_db():
    conn = sqlite3.connect("clients.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            api_key TEXT PRIMARY KEY,
            name TEXT,
            usage_count INTEGER DEFAULT 0,
            usage_limit INTEGER
