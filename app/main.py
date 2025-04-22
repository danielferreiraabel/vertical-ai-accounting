from fastapi import FastAPI, Request, HTTPException, Header
from pydantic import BaseModel
import openai
import os
from db import init_db, validate_api_key, increment_usage

# Inicializa o banco de dados
init_db()

openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI(title="Vertical AI Accounting")

class ExpenseIn(BaseModel):
    description: str

@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.post("/categorize")
async def categorize_expense(
    item: ExpenseIn,
    request: Request,
    x_api_key: str = Header(...)
):
    # Verifica a chave do cliente
    if not validate_api_key(x_api_key):
        raise HTTPException(status_code=403, detail="Chave inválida ou limite de uso atingido.")

    try:
        client = openai.OpenAI(api_key=openai.api_key)

        chat_completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Você é um assistente contábil profissional. "
                        "Classifique a despesa fornecida em uma categoria contábil adequada, "
                        "utilizando linguagem simples e sempre respondendo em português. "
                        "Prefira categorias como Aluguel, Transporte, Serviços, Marketing, etc."
                    )
                },
                {
                    "role": "user",
                    "content": f"Classifique esta despesa: {item.description}"
                }
            ]
        )

        # Marca mais 1 uso
        increment_usage(x_api_key)

        return {
            "categoria": chat_completion.choices[0].message.content.strip()
        }

    except Exception as e:
        return {"erro": str(e)}
from db import get_client_info  # já deve estar no topo

@app.get("/me")
def get_my_info(x_api_key: str = Header(...)):
    info = get_client_info(x_api_key)
    if info:
        return info
    raise HTTPException(status_code=403, detail="Chave inválida.")
