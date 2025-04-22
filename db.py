import sqlite3

# Cria o banco e a tabela
def init_db():
    conn = sqlite3.connect("clients.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            api_key TEXT PRIMARY KEY,
            name TEXT,
            usage_count INTEGER DEFAULT 0,
            usage_limit INTEGER DEFAULT 1000
        )
    """)
    conn.commit()
    conn.close()

# Valida a chave
def validate_api_key(api_key):
    conn = sqlite3.connect("clients.db")
    cursor = conn.cursor()
    cursor.execute("SELECT usage_count, usage_limit FROM clients WHERE api_key = ?", (api_key,))
    result = cursor.fetchone()
    conn.close()

    if result:
        usage_count, usage_limit = result
        return usage_count < usage_limit
    return False

# Soma +1 ao uso da chave
def increment_usage(api_key):
    conn = sqlite3.connect("clients.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE clients SET usage_count = usage_count + 1 WHERE api_key = ?", (api_key,))
    conn.commit()
    conn.close()

