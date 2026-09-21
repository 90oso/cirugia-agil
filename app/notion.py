"""Sincronización con Notion API 2025-09-03."""

import asyncio
import json

import httpx

from .config import Settings
from .storage import Store


class NotionError(RuntimeError):
    pass


# ============================================================
# HELPERS
# ============================================================

def rich(text):
    """
    Convierte texto plano al formato rich_text de Notion.
    Se divide en fragmentos para evitar superar límites.
    """
    text = str(text or "")

    return [
        {
            "type": "text",
            "text": {
                "content": text[i:i + 1900]
            }
        }
        for i in range(0, len(text), 1900)
    ] or []


def _text(items):
    """
    Extrae texto de propiedades title/rich_text.
    """
    return "".join(
        item.get("plain_text")
        or item.get("text", {}).get("content", "")
        for item in items
    )


def property_value(page, name):
    """
    Obtiene el valor de una propiedad de una página de Notion.
    """
    prop = page.get("properties", {}).get(name)

    if not prop:
        return None

    kind = prop.get("type")

    if kind == "title":
        return _text(
            prop.get("title", [])
        )

    if kind == "rich_text":
        return _text(
            prop.get("rich_text", [])
        )

    if kind == "select":
        value = prop.get("select")
        return value.get("name") if value else None

    if kind == "status":
        value = prop.get("status")
        return value.get("name") if value else None

    if kind == "date":
        value = prop.get("date")
        return value.get("start") if value else None

    if kind == "number":
        return prop.get("number")

    if kind == "checkbox":
        return prop.get("checkbox")

    return None


# ============================================================
# NOTION
# ============================================================

class Notion:

    def __init__(self, cfg: Settings):
        self.cfg = cfg

        # No ponemos Content-Type aquí porque upload()
        # utiliza multipart/form-data.
        self.headers = {
            "Authorization": f"Bearer {cfg.notion_token}",
            "Notion-Version": "2025-09-03",
        }

    # ========================================================
    # HTTP
    # ========================================================

    async def call(
        self,
        method,
        path,
        **kwargs
    ):
        """
        Ejecuta llamadas a Notion con reintentos
        para errores transitorios de conexión.
        """

        if not self.cfg.notion_token:
            raise NotionError(
                "Falta NOTION_TOKEN en .env."
            )

        url = (
            "https://api.notion.com/v1"
            + path
        )

        last_error = None

        for attempt in range(3):
            try:
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(
                        60,
                        connect=15
                    ),
                    http2=False,
                ) as client:

                    response = await client.request(
                        method,
                        url,
                        headers=self.headers,
                        **kwargs
                    )

                if response.is_error:
                    raise NotionError(
                        f"Notion HTTP "
                        f"{response.status_code}: "
                        f"{response.text}"
                    )

                if not response.content:
                    return {}

                return response.json()

            except NotionError:
                raise

            except (
                httpx.RemoteProtocolError,
                httpx.ConnectError,
                httpx.ConnectTimeout,
                httpx.ReadError,
                httpx.ReadTimeout,
                httpx.WriteError,
                httpx.WriteTimeout,
                httpx.PoolTimeout,
            ) as exc:

                last_error = exc

                if attempt < 2:
                    await asyncio.sleep(
                        1.5 * (attempt + 1)
                    )

        raise NotionError(
            "No se pudo conectar con Notion "
            "después de 3 intentos: "
            f"{last_error}"
        ) from last_error

    # ========================================================
    # DATA SOURCES
    # ========================================================

    async def query_source(
        self,
        source_id,
        filter_data=None
    ):
        """
        Consulta un Data Source de Notion.
        """

        if not source_id:
            raise NotionError(
                "Falta un Data Source ID "
                "en la configuración."
            )

        body = {
            "page_size": 100
        }

        if filter_data:
            body["filter"] = filter_data

        return await self.call(
            "POST",
            f"/data_sources/{source_id}/query",
            json=body
        )

    # ========================================================
    # PACIENTES
    # ========================================================

    async def get_patient_by_policy(
        self,
        policy_number
    ):
        """
        Busca el paciente correspondiente
        al número de póliza.
        """

        data = await self.query_source(
            self.cfg.notion_patients_source,
            {
                "property": "Número Póliza",
                "rich_text": {
                    "equals": policy_number
                }
            }
        )

        results = data.get(
            "results",
            []
        )

        if not results:
            return None

        page = results[0]

        return {
            "paciente":
                property_value(
                    page,
                    "Paciente"
                ),

            "id_paciente":
                property_value(
                    page,
                    "ID Paciente"
                ),

            "documento":
                property_value(
                    page,
                    "Documento"
                ),

            "numero_poliza":
                property_value(
                    page,
                    "Número Póliza"
                ),
        }

    # ========================================================
    # POLIZAS
    # ========================================================

    async def get_policy(
        self,
        policy_number
    ):
        """
        Busca una póliza por su número.
        """

        data = await self.query_source(
            self.cfg.notion_policies_source,
            {
                "property": "Número Póliza",
                "title": {
                    "equals": policy_number
                }
            }
        )

        results = data.get(
            "results",
            []
        )

        if not results:
            return None

        page = results[0]

        return {
            "numero_poliza":
                property_value(
                    page,
                    "Número Póliza"
                ),

            "id_paciente":
                property_value(
                    page,
                    "ID Paciente"
                ),

            "plan":
                property_value(
                    page,
                    "Plan"
                ),

            "estado":
                property_value(
                    page,
                    "Estado"
                ),

            "fecha_inicio":
                property_value(
                    page,
                    "Fecha Inicio"
                ),

            "fecha_vencimiento":
                property_value(
                    page,
                    "Fecha Vencimiento"
                ),
        }

    # ========================================================
    # COBERTURAS
    # ========================================================

    async def get_coverages(
        self,
        plan
    ):
        """
        Obtiene las coberturas correspondientes
        al plan de la póliza.
        """

        data = await self.query_source(
            self.cfg.notion_coverages_source,
            {
                "property": "Plan",
                "rich_text": {
                    "equals": plan
                }
            }
        )

        coverages = []

        for page in data.get(
            "results",
            []
        ):
            documents_text = (
                property_value(
                    page,
                    "Documentos Requeridos"
                )
                or ""
            )

            documents = [
                item.strip()
                for item
                in documents_text.split(",")
                if item.strip()
            ]

            coverages.append(
                {
                    "cobertura":
                        property_value(
                            page,
                            "Cobertura"
                        ),

                    "plan":
                        property_value(
                            page,
                            "Plan"
                        ),

                    "codigo":
                        property_value(
                            page,
                            "Código"
                        ),

                    "procedimiento":
                        property_value(
                            page,
                            "Procedimiento"
                        ),

                    "cubierto":
                        property_value(
                            page,
                            "Cubierto"
                        ),

                    "carencia_dias":
                        property_value(
                            page,
                            "Carencia Días"
                        ),

                    "documentos_requeridos":
                        documents,

                    "exclusiones":
                        property_value(
                            page,
                            "Exclusiones"
                        ),
                }
            )

        return coverages

    # ========================================================
    # CONTEXTO COMPLETO
    # ========================================================

    async def get_case_context(
        self,
        policy_number
    ):
        """
        Construye el contexto completo del caso:
        paciente + póliza + coberturas.
        """

        patient = (
            await self.get_patient_by_policy(
                policy_number
            )
        )

        policy = (
            await self.get_policy(
                policy_number
            )
        )

        if not patient:
            raise NotionError(
                f"No existe un paciente "
                f"asociado a {policy_number}."
            )

        if not policy:
            raise NotionError(
                f"No existe la póliza "
                f"{policy_number}."
            )

        plan = policy.get("plan")

        if not plan:
            raise NotionError(
                "La póliza no tiene "
                "un plan configurado."
            )

        coverages = (
            await self.get_coverages(
                plan
            )
        )

        if not coverages:
            raise NotionError(
                "No hay coberturas configuradas "
                f"para el plan {plan}."
            )

        return {
            "patient": patient,
            "policy": policy,
            "coverages": coverages,
        }

    # ========================================================
    # GUARDAR RESULTADO EN SOLICITUDES
    # ========================================================

    async def save_request(
        self,
        result
    ):
        """
        Guarda el resultado estructurado del agente
        en la tabla Solicitudes.
        """

        if not self.cfg.notion_requests_source:
            raise NotionError(
                "Falta "
                "NOTION_REQUESTS_DATA_SOURCE_ID "
                "en .env."
            )

        extraction = result.get(
            "extraction",
            {}
        )

        surgery_date = (
            extraction
            .get(
                "surgery_date",
                {}
            )
            .get("value")
        )

        missing = result.get(
            "missing_documents",
            []
        )

        checks = result.get(
            "checks",
            []
        )

        policy_number = (
            result.get(
                "policy_number",
                ""
            )
            or ""
        )

        patient = (
            result.get(
                "patient",
                ""
            )
            or ""
        )

        procedure = (
            result.get(
                "procedure",
                ""
            )
            or "Solicitud quirúrgica"
        )

        status = (
            result.get(
                "status",
                "REVISION_HUMANA"
            )
            or "REVISION_HUMANA"
        )

        summary = (
            result.get(
                "summary",
                ""
            )
            or ""
        )

        title = (
            f"{policy_number} - "
            f"{procedure}"
        )

        evidence_text = json.dumps(
            checks,
            ensure_ascii=False
        )

        # Evitamos generar cantidades excesivas de
        # rich_text para la demostración.
        evidence_text = evidence_text[:6000]

        properties = {
            "Solicitud": {
                "title": rich(
                    title
                )
            },

            "Número Póliza": {
                "rich_text": rich(
                    policy_number
                )
            },

            "Paciente": {
                "rich_text": rich(
                    patient
                )
            },

            "Procedimiento": {
                "rich_text": rich(
                    procedure
                )
            },

            "Estado": {
                "select": {
                    "name": status
                }
            },

            "Documentos Faltantes": {
                "rich_text": rich(
                    ", ".join(missing)
                    if missing
                    else "Ninguno"
                )
            },

            "Análisis IA": {
                "rich_text": rich(
                    summary
                )
            },

            "Evidencia": {
                "rich_text": rich(
                    evidence_text
                )
            },
        }

        if surgery_date:
            properties[
                "Fecha Cirugía"
            ] = {
                "date": {
                    "start":
                        surgery_date
                }
            }

        body = {
            "parent": {
                "type":
                    "data_source_id",

                "data_source_id":
                    self.cfg
                    .notion_requests_source,
            },

            "properties":
                properties,
        }

        return await self.call(
            "POST",
            "/pages",
            json=body
        )

    # ========================================================
    # SUBIDA DE ARCHIVOS
    # ========================================================

    async def upload(
        self,
        path,
        filename,
        mime
    ):
        """
        Sube un archivo original a Notion.
        """

        created = await self.call(
            "POST",
            "/file_uploads",
            json={
                "mode": "single_part",
                "filename": filename,
                "content_type": mime,
            }
        )

        upload_id = created.get("id")

        if not upload_id:
            raise NotionError(
                "Notion no devolvió un ID "
                "para la subida del archivo."
            )

        with path.open("rb") as file:
            await self.call(
                "POST",
                f"/file_uploads/{upload_id}/send",
                files={
                    "file": (
                        filename,
                        file,
                        mime
                    )
                }
            )

        return {
            "object": "block",
            "type": "file",
            "file": {
                "type": "file_upload",
                "file_upload": {
                    "id": upload_id
                },
                "name": filename,
            }
        }

    # ========================================================
    # SINCRONIZACION COMPLETA LEGACY
    # ========================================================

    async def sync(
        self,
        result,
        store: Store
    ):
        """
        Conserva el flujo original de sincronización:
        crea una página y adjunta los documentos originales.

        Se mantiene por compatibilidad con el proyecto anterior.
        """

        if (
            result.get("notion")
            and result["notion"].get(
                "complete",
                True
            )
        ):
            return result["notion"]

        if not self.cfg.notion_ready:
            raise NotionError(
                "Configura NOTION_TOKEN y "
                "NOTION_DATA_SOURCE_ID en .env "
                "y reinicia la aplicación."
            )

        source = await self.call(
            "GET",
            f"/data_sources/"
            f"{self.cfg.notion_data_source}"
        )

        title_key = next(
            (
                key
                for key, value
                in source.get(
                    "properties",
                    {}
                ).items()
                if value.get("type")
                == "title"
            ),
            None
        )

        if not title_key:
            raise NotionError(
                "La base de Notion no tiene "
                "una propiedad de título."
            )

        blocks = [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": rich(
                        result.get(
                            "summary",
                            ""
                        )
                    )
                }
            }
        ]

        blocks.append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": rich(
                        f"Solicitud "
                        f"{result.get('id', '')} | "
                        f"{result.get('created_at', '')} | "
                        f"Modelo: "
                        f"{result.get('model', '')}\n"
                        f"{result.get('disclaimer', '')}"
                    )
                }
            }
        )

        for check in result.get(
            "checks",
            []
        ):
            body = (
                f"{check.get('name', '')} "
                f"[{check.get('status', '')}]: "
                f"{check.get('detail', '')}"
            )

            for evidence in check.get(
                "evidence",
                []
            ):
                body += (
                    f"\n"
                    f"{evidence.get('document', '')}, "
                    f"página "
                    f"{evidence.get('page', '')}: "
                    f"{evidence.get('quote', '')}"
                )

            blocks.append(
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text":
                            rich(body)
                    }
                }
            )

        for doc in result.get(
            "documents",
            []
        ):
            disk_name = doc.get(
                "disk_name"
            )

            if not disk_name:
                continue

            path = (
                store.root
                / result["id"]
                / disk_name
            )

            blocks.append(
                await self.upload(
                    path,
                    doc.get(
                        "name",
                        disk_name
                    ),
                    doc.get(
                        "mime",
                        "application/octet-stream"
                    )
                )
            )

        # Una página por solicitud.
        if not result.get("notion"):
            page = await self.call(
                "POST",
                "/pages",
                json={
                    "parent": {
                        "type":
                            "data_source_id",

                        "data_source_id":
                            self.cfg
                            .notion_data_source,
                    },

                    "properties": {
                        title_key: {
                            "title": rich(
                                f"{result.get('patient') or 'Solicitud'} "
                                f"- {result.get('title', '')}"
                            )
                        }
                    },

                    "children":
                        blocks[:100],
                }
            )

            result["notion"] = {
                "page_id":
                    page["id"],

                "url":
                    page.get("url"),

                "next_offset":
                    100,

                "complete":
                    False,
            }

            store.update(
                result
            )

        start = result[
            "notion"
        ].get(
            "next_offset",
            100
        )

        for offset in range(
            start,
            len(blocks),
            100
        ):
            await self.call(
                "PATCH",
                (
                    f'/blocks/'
                    f'{result["notion"]["page_id"]}'
                    f'/children'
                ),
                json={
                    "children":
                        blocks[
                            offset:
                            offset + 100
                        ]
                }
            )

            result[
                "notion"
            ][
                "next_offset"
            ] = offset + 100

            store.update(
                result
            )

        result[
            "notion"
        ][
            "complete"
        ] = True

        store.update(
            result
        )

        return result[
            "notion"
        ]

    # ========================================================
    # CREAR BASE LEGACY
    # ========================================================

    async def create_database(self):
        """
        Se mantiene para compatibilidad con
        el proyecto original.
        """

        if (
            not self.cfg.notion_token
            or not self.cfg.notion_parent_page
        ):
            raise NotionError(
                "Configura NOTION_TOKEN y "
                "NOTION_PARENT_PAGE_ID en .env."
            )

        return await self.call(
            "POST",
            "/databases",
            json={
                "parent": {
                    "type": "page_id",
                    "page_id":
                        self.cfg.notion_parent_page,
                },

                "title":
                    rich(
                        "Cirugía Ágil - Solicitudes"
                    ),

                "initial_data_source": {
                    "properties": {
                        "Solicitud": {
                            "title": {}
                        }
                    }
                },
            }
        )