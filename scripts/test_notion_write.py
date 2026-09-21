import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import settings
from app.notion import Notion


async def main():
    notion = Notion(settings)

    result = {
        "status": "DOCUMENTOS_FALTANTES",
        "patient": "Ana Ejemplo",
        "policy_number": "POL-001",
        "procedure": "Reparación de hernia inguinal",
        "summary": (
            "Faltan documentos requeridos para completar "
            "la preautorización."
        ),
        "missing_documents": [
            "Orden quirúrgica",
            "Ultrasonido",
        ],
        "checks": [
            {
                "name": "Cobertura",
                "status": "pass",
                "detail": "Procedimiento cubierto.",
            },
            {
                "name": "Orden quirúrgica",
                "status": "missing",
                "detail": "Documento no aportado.",
            },
        ],
        "extraction": {
            "surgery_date": {
                "value": "2026-10-15"
            }
        },
    }

    response = await notion.save_request(result)

    print("GUARDADO CORRECTAMENTE")
    print("ID:", response.get("id"))
    print("URL:", response.get("url"))


asyncio.run(main())