import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import settings
from app.ai import probe


async def main():
    result = await probe(
        settings,
        settings.model
    )

    print(result)


asyncio.run(main())