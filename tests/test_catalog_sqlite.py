import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from app.catalog import CatalogError, SqliteCatalog

class CatalogTests(unittest.TestCase):
    def test_creates_private_empty_schema_and_reports_missing_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = SqliteCatalog(SimpleNamespace(data_dir=Path(directory)))
            self.assertEqual(repo.count_policies(), 0)
            with self.assertRaises(CatalogError):
                asyncio.run(repo.get_case_context("POL-UNKNOWN"))

    def test_reads_joined_patient_policy_and_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = SqliteCatalog(SimpleNamespace(data_dir=Path(directory)))
            with repo._connection() as conn:
                conn.execute("INSERT INTO patients(id,name) VALUES ('P1','Paciente Simulado')")
                conn.execute("INSERT INTO policies VALUES ('POL1','P1','Integral','Activa','2026-01-01','2027-01-01')")
                conn.execute("""INSERT INTO coverages(plan,code,procedure,covered,waiting_days,required_documents)
                                VALUES ('Integral','X01','Procedimiento de prueba',1,180,'["Orden"]')""")
                conn.commit()
            case = asyncio.run(repo.get_case_context("POL1"))
            self.assertEqual(case["policy"]["id_paciente"], case["patient"]["id_paciente"])
            self.assertEqual(case["coverages"][0]["documentos_requeridos"], ["Orden"])

if __name__ == "__main__":
    unittest.main()
