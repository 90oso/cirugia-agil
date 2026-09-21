import asyncio
import json
import time
from datetime import date

from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    Request,
)
from fastapi.responses import (
    FileResponse,
    JSONResponse,
    Response,
)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import ai
from .config import Settings, ROOT, settings
from .documents import (
    Document,
    DocumentError,
    extract_document,
)
from .notion import Notion, NotionError
from .rules import evaluate
from .storage import Store


# ============================================================
# MODELOS DE API
# ============================================================

class ModelRequest(BaseModel):
    model: str = Field(
        min_length=1,
        max_length=160
    )


# ============================================================
# DOCUMENTOS VIRTUALES GENERADOS DESDE NOTION
# ============================================================

def build_policy_document(context):
    """
    Convierte los datos estructurados de Notion en un
    documento textual verificable por Gemini y rules.py.
    """

    policy = context["policy"]
    patient = context["patient"]

    lines = [
        "FUENTE: Base de datos Notion de la aseguradora.",
        f"Número de póliza: {policy['numero_poliza']}",
        f"ID del asegurado: {policy['id_paciente']}",
        f"Nombre del asegurado: {patient['paciente']}",
        f"Estado de póliza: {policy['estado']}",
        (
            "Fecha de inicio de cobertura: "
            f"{policy['fecha_inicio']}"
        ),
        (
            "Fecha de vencimiento: "
            f"{policy['fecha_vencimiento']}"
        ),
        f"Plan: {policy['plan']}",
        "",
        "COBERTURAS DEL PLAN:",
    ]

    for coverage in context["coverages"]:
        required_documents = ", ".join(
            coverage["documentos_requeridos"]
        ) or "Ninguno"

        lines.extend([
            "",
            f"Código: {coverage['codigo']}",
            (
                "Procedimiento: "
                f"{coverage['procedimiento']}"
            ),
            (
                "Cubierto: "
                f"{'Sí' if coverage['cubierto'] else 'No'}"
            ),
            (
                "Carencia días: "
                f"{coverage['carencia_dias']}"
            ),
            (
                "Documentos requeridos: "
                f"{required_documents}"
            ),
            (
                "Exclusiones: "
                f"{coverage['exclusiones'] or 'Ninguna registrada'}"
            ),
        ])

    text = "\n".join(lines)

    return Document(
        id="poliza",
        name="poliza_desde_notion.txt",
        content=text.encode("utf-8"),
        pages=[text],
        mime="text/plain",
    )


def build_request_document(
    policy_number,
    surgery_date
):
    """
    Crea un documento interno con los datos de la
    solicitud introducidos por el usuario.
    """

    text = (
        "Número de póliza indicado en la solicitud: "
        f"{policy_number}\n"
        "Fecha prevista de cirugía: "
        f"{surgery_date}\n"
    )

    return Document(
        id="solicitud",
        name="datos_solicitud.txt",
        content=text.encode("utf-8"),
        pages=[text],
        mime="text/plain",
    )


# ============================================================
# APLICACIÓN
# ============================================================

def create_app(cfg: Settings):

    app = FastAPI(
        title="Cirugía Ágil",
        version="1.0.0",
        docs_url=None,
        redoc_url=None,
    )

    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[
            "localhost",
            "127.0.0.1",
            "[::1]",
            "testserver",
        ],
    )

    store = Store(cfg)

    ai_lock = asyncio.Lock()
    notion_lock = asyncio.Lock()

    # ========================================================
    # SEGURIDAD LOCAL
    # ========================================================

    @app.middleware("http")
    async def local_boundaries(
        request: Request,
        call_next
    ):

        if request.method in (
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
        ):
            origin = request.headers.get(
                "origin"
            )

            expected_origin = (
                f"{request.url.scheme}://"
                f"{request.headers.get('host')}"
            )

            if (
                origin
                and origin != expected_origin
            ):
                return JSONResponse(
                    {
                        "detail":
                            "La solicitud debe proceder "
                            "de la aplicación local."
                    },
                    status_code=403,
                )

            if (
                request.headers.get(
                    "sec-fetch-site"
                )
                == "cross-site"
            ):
                return JSONResponse(
                    {
                        "detail":
                            "Origen no permitido."
                    },
                    status_code=403,
                )

            content_length = int(
                request.headers.get(
                    "content-length",
                    "0",
                )
                or 0
            )

            if (
                content_length
                > 30 * 1024 * 1024
            ):
                return JSONResponse(
                    {
                        "detail":
                            "La carga completa "
                            "supera 30 MB."
                    },
                    status_code=413,
                )

        response = await call_next(
            request
        )

        response.headers[
            "X-Content-Type-Options"
        ] = "nosniff"

        response.headers[
            "Referrer-Policy"
        ] = "no-referrer"

        response.headers[
            "Content-Security-Policy"
        ] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "object-src 'none'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

        if request.url.path.startswith(
            "/api"
        ):
            response.headers[
                "Cache-Control"
            ] = "no-store"

        return response

    # ========================================================
    # EXCEPCIONES
    # ========================================================

    @app.exception_handler(ai.AIError)
    async def ai_error(
        request,
        exc
    ):
        return JSONResponse(
            {
                "detail": str(exc)
            },
            status_code=503,
        )

    @app.exception_handler(
        DocumentError
    )
    async def doc_error(
        request,
        exc
    ):
        return JSONResponse(
            {
                "detail": str(exc)
            },
            status_code=422,
        )

    @app.exception_handler(
        NotionError
    )
    async def notion_error(
        request,
        exc
    ):
        return JSONResponse(
            {
                "detail": str(exc)
            },
            status_code=502,
        )

    # ========================================================
    # HEALTH
    # ========================================================

    @app.get("/api/health")
    async def health():

        try:
            models = await ai.list_models(
                cfg
            )

            connected = True
            error = None

        except (
            ai.AIError,
            ValueError,
        ) as exc:

            models = []
            connected = False
            error = str(exc)

        return {
            "ok": True,

            # Nombre actual
            "gemini_connected":
                connected,

            # Compatibilidad temporal
            # con el frontend anterior.
            "ollama_connected":
                connected,

            "models":
                models,

            "default_model":
                cfg.model,

            "notion_configured":
                cfg.notion_catalog_ready,

            "max_file_mb":
                (
                    cfg.max_file_bytes
                    // 1024
                    // 1024
                ),

            "max_text_chars":
                cfg.max_chars,

            "error":
                error,
        }

    # ========================================================
    # PRUEBA DEL MODELO
    # ========================================================

    @app.post("/api/model/test")
    async def model_test(
        body: ModelRequest
    ):

        ai.valid_model(
            body.model
        )

        async with ai_lock:

            available = (
                await ai.list_models(
                    cfg
                )
            )

            if body.model not in available:
                raise ai.AIError(
                    "El modelo solicitado "
                    "no está configurado."
                )

            return await ai.probe(
                cfg,
                body.model
            )

    # ========================================================
    # ANALIZAR SOLICITUD
    # ========================================================

    @app.post("/api/analyze")
    async def analyze(
        policy_number: str = Form(...),
        surgery_date: str = Form(...),
        report: UploadFile = File(...),
        model: str = Form(...),
        attachments: (
            list[UploadFile] | None
        ) = File(None),
    ):

        # ----------------------------------------------------
        # 1. Validaciones básicas
        # ----------------------------------------------------

        ai.valid_model(
            model
        )

        policy_number = (
            policy_number.strip()
        )

        if not policy_number:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Introduce un número "
                    "de póliza."
                ),
            )

        try:
            date.fromisoformat(
                surgery_date
            )

        except ValueError:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Fecha de cirugía "
                    "inválida."
                ),
            )

        started = time.monotonic()

        # ----------------------------------------------------
        # 2. Consultar Notion
        # ----------------------------------------------------

        notion = Notion(
            cfg
        )

        context = (
            await notion.get_case_context(
                policy_number
            )
        )

        # ----------------------------------------------------
        # 3. Verificar asociación paciente-póliza
        # ----------------------------------------------------

        patient_id = (
            context[
                "patient"
            ][
                "id_paciente"
            ]
            or ""
        ).strip()

        insured_id = (
            context[
                "policy"
            ][
                "id_paciente"
            ]
            or ""
        ).strip()

        if patient_id != insured_id:
            raise HTTPException(
                status_code=409,
                detail=(
                    "El paciente y la póliza "
                    "de Notion no corresponden "
                    "al mismo ID."
                ),
            )

        # ----------------------------------------------------
        # 4. Construir documentos internos
        # ----------------------------------------------------

        documents = [
            build_policy_document(
                context
            ),
            build_request_document(
                policy_number,
                surgery_date,
            ),
        ]

        # ----------------------------------------------------
        # 5. Leer informe médico
        # ----------------------------------------------------

        report_data = (
            await report.read(
                cfg.max_file_bytes + 1
            )
        )

        await report.close()

        if (
            len(report_data)
            > cfg.max_file_bytes
        ):
            raise HTTPException(
                status_code=413,
                detail=(
                    f"{report.filename}: "
                    f"máximo "
                    f"{cfg.max_file_bytes // 1024 // 1024} MB."
                ),
            )

        report_document = (
            await asyncio.to_thread(
                extract_document,
                "informe",
                report.filename or "",
                report_data,
            )
        )

        documents.append(
            report_document
        )

        # ----------------------------------------------------
        # 6. Leer anexos
        # ----------------------------------------------------

        extra = [
            uploaded
            for uploaded
            in (attachments or [])
            if uploaded.filename
        ]

        if len(extra) > 3:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Máximo tres anexos."
                ),
            )

        for index, uploaded in enumerate(
            extra,
            start=1,
        ):

            data = await uploaded.read(
                cfg.max_file_bytes + 1
            )

            await uploaded.close()

            if (
                len(data)
                > cfg.max_file_bytes
            ):
                raise HTTPException(
                    status_code=413,
                    detail=(
                        f"{uploaded.filename}: "
                        f"máximo "
                        f"{cfg.max_file_bytes // 1024 // 1024} MB."
                    ),
                )

            document = (
                await asyncio.to_thread(
                    extract_document,
                    f"anexo{index}",
                    uploaded.filename or "",
                    data,
                )
            )

            documents.append(
                document
            )

        # ----------------------------------------------------
        # 7. Gemini analiza
        # ----------------------------------------------------

        async with ai_lock:

            available = (
                await ai.list_models(
                    cfg
                )
            )

            if model not in available:
                raise ai.AIError(
                    "Modelo no disponible."
                )

            extraction = (
                await ai.extract(
                    cfg,
                    model,
                    documents,
                )
            )

        # ----------------------------------------------------
        # 8. Python verifica y decide
        # ----------------------------------------------------

        result = evaluate(
            extraction,
            documents,
        )

        result.update(
            extraction=(
                extraction.model_dump()
            ),

            patient=(
                extraction
                .patient_name
                .value
                or context[
                    "patient"
                ][
                    "paciente"
                ]
            ),

            procedure=(
                extraction
                .requested_procedure
                .value
            ),

            policy_number=
                policy_number,

            notion_context=
                context,
        )

        # ----------------------------------------------------
        # 9. Guardar localmente
        # ----------------------------------------------------

        saved = store.save(
            result,
            documents,
            model,
            time.monotonic()
            - started,
        )

        # ----------------------------------------------------
        # 10. Guardar automáticamente en Notion
        # ----------------------------------------------------

        try:
            async with notion_lock:

                notion_result = (
                    await notion.save_request(
                        saved
                    )
                )

            saved["notion"] = {
                "page_id":
                    notion_result.get(
                        "id"
                    ),

                "url":
                    notion_result.get(
                        "url"
                    ),

                "complete":
                    True,
            }

            saved[
                "notion_sync_error"
            ] = None

        except NotionError as exc:

            # El análisis no se pierde si
            # Notion falla temporalmente.
            saved["notion"] = None

            saved[
                "notion_sync_error"
            ] = str(exc)

        store.update(
            saved
        )

        return saved

    # ========================================================
    # HISTORIAL
    # ========================================================

    @app.get("/api/cases")
    async def cases():
        return store.recent()

    def get_case(
        case_id
    ):
        result = store.get(
            case_id
        )

        if not result:
            raise HTTPException(
                status_code=404,
                detail=(
                    "No se encontró "
                    "la solicitud."
                ),
            )

        return result

    @app.get(
        "/api/cases/{case_id}"
    )
    async def case(
        case_id: str
    ):
        return get_case(
            case_id
        )

    # ========================================================
    # EXPORTAR RESULTADO
    # ========================================================

    @app.get(
        "/api/cases/{case_id}/export"
    )
    async def export(
        case_id: str
    ):

        result = get_case(
            case_id
        )

        export_result = (
            json.loads(
                json.dumps(
                    result,
                    ensure_ascii=False,
                )
            )
        )

        for doc in export_result.get(
            "documents",
            []
        ):
            doc.pop(
                "disk_name",
                None
            )

        return Response(
            json.dumps(
                export_result,
                ensure_ascii=False,
                indent=2,
            ),
            media_type=(
                "application/json"
            ),
            headers={
                "Content-Disposition":
                    (
                        'attachment; '
                        f'filename="solicitud_'
                        f'{result["id"][:8]}.json"'
                    )
            },
        )

    # ========================================================
    # DESCARGAR DOCUMENTOS
    # ========================================================

    @app.get(
        "/api/cases/"
        "{case_id}/documents/"
        "{document_id}"
    )
    async def document(
        case_id: str,
        document_id: str,
    ):

        result = get_case(
            case_id
        )

        entry = next(
            (
                item
                for item
                in result.get(
                    "documents",
                    []
                )
                if item["id"]
                == document_id
            ),
            None,
        )

        if not entry:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Documento no encontrado."
                ),
            )

        path = (
            store.root
            / result["id"]
            / entry["disk_name"]
        )

        if not path.is_file():
            raise HTTPException(
                status_code=404,
                detail=(
                    "El archivo original "
                    "no está en la carpeta data."
                ),
            )

        return FileResponse(
            path,
            filename=entry["name"],
            media_type=entry["mime"],
        )

    # ========================================================
    # REINTENTAR SINCRONIZACIÓN CON NOTION
    # ========================================================

    @app.post(
        "/api/cases/{case_id}/notion"
    )
    async def sync_notion(
        case_id: str
    ):

        async with notion_lock:

            result = get_case(
                case_id
            )

            notion = Notion(
                cfg
            )

            try:
                notion_result = (
                    await notion.save_request(
                        result
                    )
                )

                result["notion"] = {
                    "page_id":
                        notion_result.get(
                            "id"
                        ),

                    "url":
                        notion_result.get(
                            "url"
                        ),

                    "complete":
                        True,
                }

                result[
                    "notion_sync_error"
                ] = None

                store.update(
                    result
                )

                return result[
                    "notion"
                ]

            except NotionError as exc:

                result[
                    "notion_sync_error"
                ] = str(exc)

                store.update(
                    result
                )

                raise

    # ========================================================
    # FRONTEND
    # ========================================================

    @app.get("/")
    async def index():
        return FileResponse(
            ROOT
            / "static"
            / "index.html"
        )

    app.mount(
        "/static",
        StaticFiles(
            directory=(
                ROOT / "static"
            )
        ),
        name="static",
    )

    return app

app = create_app(
    settings
)