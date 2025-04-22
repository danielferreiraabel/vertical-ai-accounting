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
# Retorna dados do cliente
def get_client_info(api_key):
    conn = sqlite3.connect("clients.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name, usage_count, usage_limit FROM clients WHERE api_key = ?", (api_key,))
    result = cursor.fetchone()
    conn.close()

    if result:
        name, usage_count, usage_limit = result
        return {
            "cliente": name,
            "usos_realizados": usage_count,
            "limite": usage_limit,
            "restante": usage_limit - usage_count
        }
    return None
    # Lista todas as chaves cadastradas
def listar_todos_clientes():
    conn = sqlite3.connect("clients.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name, api_key, usage_count, usage_limit FROM clients")
    resultados = cursor.fetchall()
    conn.close()

    lista = []
    for row in resultados:
        lista.append({
            "cliente": row[0],
            "api_key": row[1],
            "usos_realizados": row[2],
            "limite": row[3],
            "restante": row[3] - row[2]
        })
    return lista


