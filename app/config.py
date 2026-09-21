from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent.parent

# Cargar siempre el .env actual del proyecto
load_dotenv(ROOT / ".env", override=True)


@dataclass(frozen=True)
class Settings:

    # -------------------------
    # Gemini
    # -------------------------

    gemini_api_key: str = os.getenv(
        "GEMINI_API_KEY",
        ""
    )

    model: str = os.getenv(
        "GEMINI_MODEL",
        "gemini-3.6-flash"
    )

    timeout: int = int(
        os.getenv(
            "GEMINI_TIMEOUT_SECONDS",
            "120"
        )
    )

    max_chars: int = int(
        os.getenv(
            "MAX_TEXT_CHARS",
            "18000"
        )
    )

    # -------------------------
    # Archivos / almacenamiento
    # -------------------------

    max_file_bytes: int = 5 * 1024 * 1024

    data_dir: Path = Path(
        os.getenv(
            "DATA_DIR",
            str(ROOT / "data")
        )
    ).resolve()

    # -------------------------
    # Notion
    # -------------------------

    notion_token: str = os.getenv(
        "NOTION_TOKEN",
        ""
    )

    notion_patients_source: str = os.getenv(
        "NOTION_PATIENTS_DATA_SOURCE_ID",
        ""
    )

    notion_policies_source: str = os.getenv(
        "NOTION_POLICIES_DATA_SOURCE_ID",
        ""
    )

    notion_coverages_source: str = os.getenv(
        "NOTION_COVERAGES_DATA_SOURCE_ID",
        ""
    )

    notion_requests_source: str = os.getenv(
        "NOTION_REQUESTS_DATA_SOURCE_ID",
        ""
    )

    # Compatibilidad con código anterior
    notion_data_source: str = os.getenv(
        "NOTION_DATA_SOURCE_ID",
        os.getenv(
            "NOTION_REQUESTS_DATA_SOURCE_ID",
            ""
        )
    )

    notion_parent_page: str = os.getenv(
        "NOTION_PARENT_PAGE_ID",
        ""
    )

    # -------------------------
    # Validaciones
    # -------------------------

    @property
    def notion_ready(self):
        return bool(
            self.notion_token
            and self.notion_data_source
        )

    @property
    def notion_catalog_ready(self):
        return bool(
            self.notion_token
            and self.notion_patients_source
            and self.notion_policies_source
            and self.notion_coverages_source
            and self.notion_requests_source
        )

    def validate_ai(self):
        if not self.gemini_api_key:
            raise ValueError(
                "Falta GEMINI_API_KEY en .env."
            )

        if not self.model:
            raise ValueError(
                "Falta GEMINI_MODEL en .env."
            )


settings = Settings()