from fastapi import FastAPI
from pydantic import BaseModel
import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI(title="Vertical AI Accounting")

class ExpenseIn(BaseModel):
    description: str

@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.post("/categorize")
async def categorize_expense(item: ExpenseIn):
    try:
        client = openai.OpenAI(api_key=openai.api_key)

        chat_completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an accounting assistant."},
                {"role": "user", "content": f"Classify this expense: {item.description}"}
            ]
        )

        return {"category": chat_completion.choices[0].message.content.strip()}

    except Exception as e:
        return {"error": str(e)}

