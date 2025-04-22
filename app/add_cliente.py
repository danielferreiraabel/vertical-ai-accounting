import sqlite3
import uuid

nova_chave = str(uuid.uuid4())
nome = "Daniel Ferreira"
limite = 1000  # Exemplo de limite alto

conn = sqlite3.connect("clients.db")
cursor = conn.cursor()

cursor.execute("INSERT INTO clients (api_key, name, usage_limit) VALUES (?, ?, ?)", 
               (nova_chave, nome, limite))

conn.commit()
conn.close()

print("Chave criada com sucesso:", nova_chave)
