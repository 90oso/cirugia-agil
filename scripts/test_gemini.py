import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=True)

api_key = os.getenv("GEMINI_API_KEY")
model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

print("API key cargada:", bool(api_key))
print("Modelo:", model)

url = "https://generativelanguage.googleapis.com/v1/interactions"

payload = {
    "model": model,
    "input": "Responde únicamente: API funcionando",
    "store": False
}

headers = {
    "x-goog-api-key": api_key,
    "Content-Type": "application/json",
}

with httpx.Client(timeout=60) as client:
    response = client.post(
        url,
        headers=headers,
        json=payload
    )

print("HTTP:", response.status_code)

if response.is_error:
    print(response.text)
    response.raise_for_status()

data = response.json()

print(data)