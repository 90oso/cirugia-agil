"""Crea una base privada en la página que el usuario configuró expresamente."""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import settings
from app.notion import Notion, NotionError

async def main():
    db = await Notion(settings).create_database()
    print('Base creada:', db.get('url', ''))
    sources = db.get('data_sources', [])
    if not sources:
        print('Consulta la fuente de datos de la base creada para obtener su ID.')
        return
    print('Copia esta línea a .env y reinicia la aplicación:')
    print('NOTION_DATA_SOURCE_ID=' + sources[0]['id'])

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except NotionError as exc:
        print('No se pudo crear la base:', exc)
        sys.exit(1)
