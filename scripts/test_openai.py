import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

api_key = os.getenv("OPENAI_API_KEY")

print("API key cargada:", bool(api_key))

client = OpenAI(api_key=api_key)

response = client.responses.create(
    model=os.getenv("OPENAI_MODEL", "gpt-5.6-luna"),
    input="Responde únicamente: API funcionando"
)

print(response.output_text)