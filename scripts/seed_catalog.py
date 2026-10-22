"""Carga únicamente registros inventados para pruebas locales de Cirugía Ágil."""
from app.config import settings
from app.catalog import SqliteCatalog

def main():
    catalog = SqliteCatalog(settings)
    with catalog._connection() as conn:
        conn.executemany("INSERT OR REPLACE INTO patients(id,name,document) VALUES (?,?,?)", [
            ("PAC-001","Ana Ejemplo","DOC-FICTICIO-01"),
            ("PAC-002","Luis Simulación","DOC-FICTICIO-02"),
            ("PAC-003","Marta Demo","DOC-FICTICIO-03"),
        ])
        conn.executemany("""
            INSERT OR REPLACE INTO policies(policy_number,patient_id,plan,state,starts_on,ends_on)
            VALUES (?,?,?,?,?,?)
        """, [
            ("POL-001","PAC-001","Integral","Activa","2025-01-01","2027-12-31"),
            ("POL-002","PAC-002","Básico","Activa","2026-07-01","2027-12-31"),
            ("POL-003","PAC-003","Integral","Vencida","2024-01-01","2026-09-30"),
        ])
        conn.executemany("""
            INSERT INTO coverages(plan,code,procedure,covered,waiting_days,required_documents,exclusions)
            VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(plan,code) DO UPDATE SET
              procedure=excluded.procedure,covered=excluded.covered,
              waiting_days=excluded.waiting_days,required_documents=excluded.required_documents,
              exclusions=excluded.exclusions
        """, [
            ("Integral","HERNIA","Reparación de hernia inguinal",1,180,'["Orden quirúrgica","Ultrasonido"]',""),
            ("Integral","RODILLA","Artroscopia de rodilla",1,365,'["Orden quirúrgica"]',""),
            ("Básico","HERNIA","Reparación de hernia inguinal",1,180,'["Orden quirúrgica","Ultrasonido"]',""),
            ("Básico","RODILLA","Artroscopia de rodilla",0,365,'["Orden quirúrgica"]',"Procedimiento fuera del plan"),
        ])
        conn.commit()
    print("Catálogo ficticio cargado:", catalog.path)
    print("Pólizas ficticias:", catalog.count_policies())

if __name__ == "__main__":
    main()
