import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import settings
from app.notion import Notion, NotionError, rich


# ============================================================
# DATOS DE DEMOSTRACIÓN
# ============================================================

PATIENTS = [
    {
        "paciente": "Ana Ejemplo",
        "id_paciente": "PAC-001",
        "documento": "8-123-456",
        "numero_poliza": "POL-001",
    },
    {
        "paciente": "Carlos Méndez",
        "id_paciente": "PAC-002",
        "documento": "8-234-567",
        "numero_poliza": "POL-002",
    },
    {
        "paciente": "Laura Gómez",
        "id_paciente": "PAC-003",
        "documento": "8-345-678",
        "numero_poliza": "POL-003",
    },
    {
        "paciente": "Miguel Torres",
        "id_paciente": "PAC-004",
        "documento": "8-456-789",
        "numero_poliza": "POL-004",
    },
    {
        "paciente": "Sofía Herrera",
        "id_paciente": "PAC-005",
        "documento": "8-567-890",
        "numero_poliza": "POL-005",
    },
]


POLICIES = [
    {
        "numero_poliza": "POL-001",
        "id_paciente": "PAC-001",
        "plan": "ORO",
        "estado": "ACTIVA",
        "fecha_inicio": "2025-01-01",
        "fecha_vencimiento": "2027-01-01",
    },
    {
        "numero_poliza": "POL-002",
        "id_paciente": "PAC-002",
        "plan": "PLATA",
        "estado": "ACTIVA",
        "fecha_inicio": "2026-06-01",
        "fecha_vencimiento": "2027-06-01",
    },
    {
        "numero_poliza": "POL-003",
        "id_paciente": "PAC-003",
        "plan": "BASICO",
        "estado": "ACTIVA",
        "fecha_inicio": "2026-01-01",
        "fecha_vencimiento": "2027-01-01",
    },
    {
        "numero_poliza": "POL-004",
        "id_paciente": "PAC-004",
        "plan": "ORO",
        "estado": "VENCIDA",
        "fecha_inicio": "2024-01-01",
        "fecha_vencimiento": "2025-01-01",
    },
    {
        "numero_poliza": "POL-005",
        "id_paciente": "PAC-005",
        "plan": "ORO",
        "estado": "ACTIVA",
        "fecha_inicio": "2025-05-01",
        "fecha_vencimiento": "2027-05-01",
    },
]


COVERAGES = [
    # ========================================================
    # PLAN ORO
    # ========================================================
    {
        "cobertura": "Hernioplastia inguinal",
        "plan": "ORO",
        "codigo": "PROC-001",
        "procedimiento": "Reparación de hernia inguinal",
        "cubierto": True,
        "carencia_dias": 180,
        "documentos_requeridos": (
            "Informe médico, orden quirúrgica, ultrasonido"
        ),
        "exclusiones": "",
    },
    {
        "cobertura": "Colecistectomía laparoscópica",
        "plan": "ORO",
        "codigo": "PROC-002",
        "procedimiento": "Colecistectomía laparoscópica",
        "cubierto": True,
        "carencia_dias": 180,
        "documentos_requeridos": (
            "Informe médico, orden quirúrgica, "
            "ultrasonido abdominal"
        ),
        "exclusiones": "",
    },
    {
        "cobertura": "Artroscopia de rodilla",
        "plan": "ORO",
        "codigo": "PROC-003",
        "procedimiento": "Artroscopia de rodilla",
        "cubierto": True,
        "carencia_dias": 90,
        "documentos_requeridos": (
            "Informe médico, orden quirúrgica, "
            "resonancia magnética"
        ),
        "exclusiones": "",
    },
    {
        "cobertura": "Apendicectomía",
        "plan": "ORO",
        "codigo": "PROC-004",
        "procedimiento": "Apendicectomía",
        "cubierto": True,
        "carencia_dias": 30,
        "documentos_requeridos": (
            "Informe médico, orden quirúrgica"
        ),
        "exclusiones": "",
    },

    # ========================================================
    # PLAN PLATA
    # ========================================================
    {
        "cobertura": "Colecistectomía laparoscópica",
        "plan": "PLATA",
        "codigo": "PROC-101",
        "procedimiento": "Colecistectomía laparoscópica",
        "cubierto": True,
        "carencia_dias": 365,
        "documentos_requeridos": (
            "Informe médico, orden quirúrgica, "
            "ultrasonido abdominal"
        ),
        "exclusiones": "",
    },
    {
        "cobertura": "Hernioplastia inguinal",
        "plan": "PLATA",
        "codigo": "PROC-102",
        "procedimiento": "Reparación de hernia inguinal",
        "cubierto": True,
        "carencia_dias": 180,
        "documentos_requeridos": (
            "Informe médico, orden quirúrgica, ultrasonido"
        ),
        "exclusiones": "",
    },
    {
        "cobertura": "Apendicectomía",
        "plan": "PLATA",
        "codigo": "PROC-103",
        "procedimiento": "Apendicectomía",
        "cubierto": True,
        "carencia_dias": 60,
        "documentos_requeridos": (
            "Informe médico, orden quirúrgica"
        ),
        "exclusiones": "",
    },

    # ========================================================
    # PLAN BASICO
    # ========================================================
    {
        "cobertura": "Artroscopia de rodilla",
        "plan": "BASICO",
        "codigo": "PROC-201",
        "procedimiento": "Artroscopia de rodilla",
        "cubierto": False,
        "carencia_dias": 180,
        "documentos_requeridos": (
            "Informe médico, orden quirúrgica, "
            "resonancia magnética"
        ),
        "exclusiones": (
            "Procedimiento no cubierto por el plan BASICO."
        ),
    },
    {
        "cobertura": "Apendicectomía",
        "plan": "BASICO",
        "codigo": "PROC-202",
        "procedimiento": "Apendicectomía",
        "cubierto": True,
        "carencia_dias": 30,
        "documentos_requeridos": (
            "Informe médico, orden quirúrgica"
        ),
        "exclusiones": "",
    },
]


# ============================================================
# COMPROBAR EXISTENCIA
# ============================================================

async def patient_exists(notion, patient_id):
    data = await notion.query_source(
        settings.notion_patients_source,
        {
            "property": "ID Paciente",
            "rich_text": {
                "equals": patient_id
            }
        }
    )

    return bool(
        data.get("results")
    )


async def policy_exists(notion, policy_number):
    data = await notion.query_source(
        settings.notion_policies_source,
        {
            "property": "Número Póliza",
            "title": {
                "equals": policy_number
            }
        }
    )

    return bool(
        data.get("results")
    )


async def coverage_exists(notion, code):
    data = await notion.query_source(
        settings.notion_coverages_source,
        {
            "property": "Código",
            "rich_text": {
                "equals": code
            }
        }
    )

    return bool(
        data.get("results")
    )


# ============================================================
# CREAR PACIENTE
# ============================================================

async def create_patient(notion, patient):
    body = {
        "parent": {
            "type": "data_source_id",
            "data_source_id":
                settings.notion_patients_source,
        },
        "properties": {
            "Paciente": {
                "title": rich(
                    patient["paciente"]
                )
            },
            "ID Paciente": {
                "rich_text": rich(
                    patient["id_paciente"]
                )
            },
            "Documento": {
                "rich_text": rich(
                    patient["documento"]
                )
            },
            "Número Póliza": {
                "rich_text": rich(
                    patient["numero_poliza"]
                )
            },
        },
    }

    return await notion.call(
        "POST",
        "/pages",
        json=body
    )


# ============================================================
# CREAR POLIZA
# ============================================================

async def create_policy(notion, policy):
    body = {
        "parent": {
            "type": "data_source_id",
            "data_source_id":
                settings.notion_policies_source,
        },
        "properties": {
            "Número Póliza": {
                "title": rich(
                    policy["numero_poliza"]
                )
            },
            "ID Paciente": {
                "rich_text": rich(
                    policy["id_paciente"]
                )
            },
            "Plan": {
                "rich_text": rich(
                    policy["plan"]
                )
            },
            "Estado": {
                "select": {
                    "name":
                        policy["estado"]
                }
            },
            "Fecha Inicio": {
                "date": {
                    "start":
                        policy["fecha_inicio"]
                }
            },
            "Fecha Vencimiento": {
                "date": {
                    "start":
                        policy["fecha_vencimiento"]
                }
            },
        },
    }

    return await notion.call(
        "POST",
        "/pages",
        json=body
    )


# ============================================================
# CREAR COBERTURA
# ============================================================

async def create_coverage(notion, coverage):
    body = {
        "parent": {
            "type": "data_source_id",
            "data_source_id":
                settings.notion_coverages_source,
        },
        "properties": {
            "Cobertura": {
                "title": rich(
                    coverage["cobertura"]
                )
            },
            "Plan": {
                "rich_text": rich(
                    coverage["plan"]
                )
            },
            "Código": {
                "rich_text": rich(
                    coverage["codigo"]
                )
            },
            "Procedimiento": {
                "rich_text": rich(
                    coverage["procedimiento"]
                )
            },
            "Cubierto": {
                "checkbox":
                    coverage["cubierto"]
            },
            "Carencia Días": {
                "number":
                    coverage["carencia_dias"]
            },
            "Documentos Requeridos": {
                "rich_text": rich(
                    coverage[
                        "documentos_requeridos"
                    ]
                )
            },
            "Exclusiones": {
                "rich_text": rich(
                    coverage["exclusiones"]
                )
            },
        },
    }

    return await notion.call(
        "POST",
        "/pages",
        json=body
    )


# ============================================================
# SEED
# ============================================================

async def main():
    notion = Notion(settings)

    print()
    print("========================================")
    print(" CIRUGIA AGIL - CARGA DE DATOS NOTION")
    print("========================================")
    print()

    # --------------------------------------------------------
    # PACIENTES
    # --------------------------------------------------------

    print("PACIENTES")
    print("----------------------------------------")

    for patient in PATIENTS:
        patient_id = (
            patient["id_paciente"]
        )

        if await patient_exists(
            notion,
            patient_id
        ):
            print(
                f"[YA EXISTE] "
                f"{patient_id} - "
                f"{patient['paciente']}"
            )
            continue

        await create_patient(
            notion,
            patient
        )

        print(
            f"[CREADO] "
            f"{patient_id} - "
            f"{patient['paciente']}"
        )

    print()

    # --------------------------------------------------------
    # POLIZAS
    # --------------------------------------------------------

    print("POLIZAS")
    print("----------------------------------------")

    for policy in POLICIES:
        number = (
            policy["numero_poliza"]
        )

        if await policy_exists(
            notion,
            number
        ):
            print(
                f"[YA EXISTE] "
                f"{number}"
            )
            continue

        await create_policy(
            notion,
            policy
        )

        print(
            f"[CREADA] "
            f"{number} - "
            f"{policy['plan']} - "
            f"{policy['estado']}"
        )

    print()

    # --------------------------------------------------------
    # COBERTURAS
    # --------------------------------------------------------

    print("COBERTURAS")
    print("----------------------------------------")

    for coverage in COVERAGES:
        code = (
            coverage["codigo"]
        )

        if await coverage_exists(
            notion,
            code
        ):
            print(
                f"[YA EXISTE] "
                f"{code} - "
                f"{coverage['procedimiento']}"
            )
            continue

        await create_coverage(
            notion,
            coverage
        )

        status = (
            "CUBIERTO"
            if coverage["cubierto"]
            else "NO CUBIERTO"
        )

        print(
            f"[CREADA] "
            f"{code} - "
            f"{coverage['plan']} - "
            f"{coverage['procedimiento']} - "
            f"{status}"
        )

    print()
    print("========================================")
    print(" DATOS DE DEMOSTRACION CARGADOS")
    print("========================================")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(
            main()
        )

    except NotionError as exc:
        print()
        print(
            "ERROR DE NOTION:"
        )
        print(
            exc
        )

    except Exception as exc:
        print()
        print(
            "ERROR:"
        )
        print(
            repr(exc)
        )