from datetime import datetime, timezone
import json
import sqlite3
from uuid import uuid4
from contextlib import contextmanager

from .config import Settings


class Store:
    def __init__(self, cfg: Settings):
        self.root = cfg.data_dir
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.root / 'cirugia_agil.sqlite3'
        with self.connect() as conn:
            conn.execute('CREATE TABLE IF NOT EXISTS cases (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL)')

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.db, timeout=10)

        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def save(self, result, documents, model, elapsed):
        case_id = uuid4().hex
        folder = self.root / case_id
        folder.mkdir()
        manifest = []
        for doc in documents:
            disk_name = f'{doc.id}_{doc.name}'
            (folder / disk_name).write_bytes(doc.content)
            manifest.append({'id': doc.id, 'name': doc.name, 'disk_name': disk_name, 'pages': len(doc.pages), 'mime': doc.mime})
        result.update(id=case_id, created_at=datetime.now(timezone.utc).isoformat(), model=model,
                      elapsed_seconds=round(elapsed, 1), documents=manifest, notion=None)
        self.update(result)
        return result

    def update(self, result):
        with self.connect() as conn:
            conn.execute('INSERT OR REPLACE INTO cases VALUES (?,?,?)',
                         (result['id'], result['created_at'], json.dumps(result, ensure_ascii=False)))

    def get(self, case_id):
        with self.connect() as conn:
            row = conn.execute('SELECT payload FROM cases WHERE id=?', (case_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def recent(self):
        with self.connect() as conn:
            rows = conn.execute('SELECT payload FROM cases ORDER BY created_at DESC LIMIT 50').fetchall()
        cases = [json.loads(row[0]) for row in rows]
        return [{k: c.get(k) for k in ('id', 'created_at', 'status', 'title', 'model', 'patient', 'procedure')} for c in cases]
