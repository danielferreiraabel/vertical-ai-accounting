from fastapi import FastAPI
import os, openai

openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI(title="Vertical AI Accounting")

@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.post("/categorize")
async def categorize_expense(description: str):
    resp = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an accounting assistant."},
            {"role": "user", "content": f"Classify this expense: {description}"}
        ]
    )
    return {"category": resp.choices[0].message.content.strip()}
