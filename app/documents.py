from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import re

from pypdf import PdfReader


class DocumentError(ValueError):
    pass


@dataclass
class Document:
    id: str
    name: str
    content: bytes
    pages: list[str]
    mime: str

    def prompt_text(self):
        return '\n'.join(f'[DOCUMENTO {self.id} | PÁGINA {i}]\n{text}' for i, text in enumerate(self.pages, 1))


def extract_document(document_id: str, filename: str, content: bytes) -> Document:
    name = Path(filename.replace('\\', '/')).name
    name = re.sub(r'[^\w.() -]', '_', name)[:150] or 'documento.txt'
    suffix = Path(name).suffix.lower()
    if not content:
        raise DocumentError(f'{name}: el archivo está vacío.')
    if suffix == '.pdf':
        try:
            reader = PdfReader(BytesIO(content))
            if reader.is_encrypted:
                raise DocumentError(f'{name}: utiliza una copia del PDF sin contraseña.')
            if len(reader.pages) > 40:
                raise DocumentError(f'{name}: máximo 40 páginas por documento.')
            pages = []
            for i, page in enumerate(reader.pages, 1):
                text = page.extract_text() or ''
                if not text.strip():
                    raise DocumentError(f'{name}, página {i}: no hay texto extraíble. Necesita OCR antes de cargarlo; no se omitió esa página.')
                if len(text) > 100000:
                    raise DocumentError(f'{name}: una página supera el límite de texto.')
                pages.append(text)
            mime = 'application/pdf'
        except DocumentError:
            raise
        except Exception as exc:
            raise DocumentError(f'{name}: no se pudo leer el PDF. Revisa que sea válido y contenga texto.') from exc
    elif suffix in ('.txt', '.md'):
        try:
            text = content.decode('utf-8-sig')
        except UnicodeDecodeError as exc:
            raise DocumentError(f'{name}: guarda el texto en codificación UTF-8.') from exc
        if '\x00' in text or not text.strip():
            raise DocumentError(f'{name}: el archivo no contiene texto válido.')
        pages = [text]
        mime = 'text/plain'
    else:
        raise DocumentError(f'{name}: usa PDF con texto, TXT o MD.')
    return Document(document_id, name, content, pages, mime)
