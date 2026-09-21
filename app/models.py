from pydantic import BaseModel, ConfigDict, Field
from typing import Literal


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Evidence(StrictModel):
    document: str = Field(description='ID exacto: poliza, informe, anexo1, anexo2...')
    page: int = Field(ge=1, description='Número de página indicado en el texto; comienza en 1.')
    quote: str = Field(min_length=1, max_length=1500, description='Cita literal y breve del documento.')


class Fact(StrictModel):
    value: str | None = Field(description='Valor textual; fechas ISO AAAA-MM-DD; números en dígitos. null si no consta.')
    evidence: list[Evidence] = Field(max_length=5)


class Requirement(StrictModel):
    name: str = Field(max_length=250)
    policy_evidence: list[Evidence] = Field(max_length=5)
    present: bool | None
    evidence: list[Evidence] = Field(max_length=5, description='Contenido del documento realmente aportado, no una mención de un adjunto ausente.')


class Condition(StrictModel):
    name: str = Field(max_length=250)
    policy_evidence: list[Evidence] = Field(max_length=5)
    fulfilled: bool | None
    evidence: list[Evidence] = Field(max_length=5)


class Extraction(StrictModel):
    policy_number: Fact
    insured_id: Fact
    coverage_start: Fact
    coverage_end: Fact
    waiting_days: Fact
    covered_procedure: Fact
    coverage_status: Literal['covered', 'excluded', 'unclear']
    coverage_evidence: list[Evidence] = Field(max_length=5)
    patient_name: Fact
    patient_id: Fact
    report_policy_number: Fact
    surgery_date: Fact
    requested_procedure: Fact
    requirements_known: bool = Field(description='true solo si se pudo identificar la lista completa de requisitos aplicables.')
    requirements_evidence: list[Evidence] = Field(max_length=5)
    documents: list[Requirement] = Field(max_length=20)
    additional_conditions: list[Condition] = Field(max_length=20)
    uncertainties: list[str] = Field(max_length=20, description='Ambigüedades, contradicciones o reglas no interpretables. Nunca ocultarlas.')
