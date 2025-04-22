from fastapi import FastAPI
from pydantic import BaseModel
import openai
import os

# Pega a chave da variável de ambiente
openai.api_key = os.getenv("OPENAI_API_KEY")

# Cria o app FastAPI
app = FastAPI(title="Vertical AI Accounting")

# Modelo para receber a requisição
class ExpenseIn(BaseModel):
    description: str

# Endpoint de teste
@app.get("/ping")
def ping():
    return {"status": "ok"}

# Endpoint principal de categorização
@app.post("/categorize")
async def categorize_expense(item: ExpenseIn):
    try:
        # Inicializa o cliente da OpenAI
        client = openai.OpenAI(api_key=openai.api_key)

        # Chamada à IA
        chat_completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Você é um assistente contábil profissional. "
                        "Classifique a despesa fornecida em uma categoria contábil adequada, "
                        "utilizando linguagem simples e sempre respondendo em português. "
                        "Prefira categorias utilizadas no Brasil, como 'Aluguel', 'Transporte', 'Marketing', 'Serviços' etc."
                    )
                },
                {
                    "role": "user",
                    "content": f"Classifique esta despesa: {item.description}"
                }
            ]
        )

        # Resposta final para o usuário
        return {
            "categoria": chat_completion.choices[0].message.content.strip()
        }

    except Exception as e:
        # Erro tratado com retorno amigável
        return {"erro": str(e)}
