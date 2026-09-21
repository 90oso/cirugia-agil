import asyncio
import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from app.config import settings
from app.notion import Notion


async def main():
    notion = Notion(settings)

    print(
        "Configuración:",
        settings.notion_catalog_ready
    )

    patient = await notion.get_patient_by_policy(
        "POL-001"
    )

    policy = await notion.get_policy(
        "POL-001"
    )

    coverages = await notion.get_coverages(
        "ORO"
    )

    print("\nPACIENTE:")
    print(patient)

    print("\nPOLIZA:")
    print(policy)

    print("\nCOBERTURAS:")
    print(coverages)

    print("\nCONTEXTO COMPLETO:")
    context = await notion.get_case_context("POL-001")
    print(context)


asyncio.run(main())