"""Catálogo propio SQLite para desarrollo/pilotos locales.
No exponer esta base con datos reales sin autenticación, cifrado, auditoría y revisión legal.
"""
import asyncio
import json
import os
import sqlite3
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS patients (
 id TEXT PRIMARY KEY,
 name TEXT NOT NULL,
 document TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS policies (
 policy_number TEXT PRIMARY KEY,
 patient_id TEXT NOT NULL REFERENCES patients(id),
 plan TEXT NOT NULL,
 state TEXT NOT NULL,
 starts_on TEXT NOT NULL,
 ends_on TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS coverages (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 plan TEXT NOT NULL,
 code TEXT NOT NULL,
 procedure TEXT NOT NULL,
 covered INTEGER NOT NULL DEFAULT 0,
 waiting_days INTEGER NOT NULL DEFAULT 0,
 required_documents TEXT NOT NULL DEFAULT '[]',
 exclusions TEXT NOT NULL DEFAULT '',
 UNIQUE(plan,code)
);
CREATE INDEX IF NOT EXISTS idx_coverages_plan ON coverages(plan);
"""

class CatalogError(RuntimeError):
    """Error de consulta o falta de datos de pólizas."""
    pass

class SqliteCatalog:
    def __init__(self, cfg):
        self.path = Path(os.getenv("CATALOG_DB_PATH") or (cfg.data_dir / "catalog.sqlite3")).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as conn:
            conn.executescript(SCHEMA)

    def _connection(self):
        conn = sqlite3.connect(str(self.path), timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _get_context(self, policy_number):
        with self._connection() as conn:
            row = conn.execute("""
                SELECT p.policy_number,p.patient_id,p.plan,p.state,p.starts_on,p.ends_on,
                       a.name,a.document
                FROM policies p JOIN patients a ON a.id=p.patient_id
                WHERE p.policy_number=?
            """, (policy_number,)).fetchone()
            if not row:
                raise CatalogError(
                    "Póliza no encontrada en el catálogo local. "
                    "Configura el catálogo antes de analizar solicitudes."
                )
            rows = conn.execute(
                "SELECT * FROM coverages WHERE plan=? ORDER BY code", (row["plan"],)
            ).fetchall()
            if not rows:
                raise CatalogError("El plan no tiene coberturas configuradas.")
            return {
                "patient": {
                    "paciente": row["name"], "id_paciente": row["patient_id"],
                    "documento": row["document"], "numero_poliza": row["policy_number"]
                },
                "policy": {
                    "numero_poliza": row["policy_number"],
                    "id_paciente": row["patient_id"], "plan": row["plan"],
                    "estado": row["state"], "fecha_inicio": row["starts_on"],
                    "fecha_vencimiento": row["ends_on"]
                },
                "coverages": [{
                    "cobertura": x["procedure"], "plan": x["plan"],
                    "codigo": x["code"], "procedimiento": x["procedure"],
                    "cubierto": bool(x["covered"]), "carencia_dias": x["waiting_days"],
                    "documentos_requeridos": json.loads(x["required_documents"]),
                    "exclusiones": x["exclusions"],
                } for x in rows]
            }

    async def get_case_context(self, policy_number):
        return await asyncio.to_thread(self._get_context, policy_number)

    def count_policies(self):
        with self._connection() as conn:
            return conn.execute("SELECT COUNT(*) FROM policies").fetchone()[0]
