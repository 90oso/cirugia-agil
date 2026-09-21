"""Reglas deterministas. El modelo extrae; Python calcula y decide el estado preliminar."""
from datetime import date, timedelta
import re
import unicodedata

from .documents import Document
from .models import Extraction, Evidence, Fact


def normal(value: str):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', value)
                           if not unicodedata.combining(c)).lower().split())


def compact(value: str):
    return re.sub(r'[^a-z0-9]', '', normal(value))

def is_missing_document_uncertainty(value: str):
    """
    Determina si una supuesta incertidumbre simplemente
    describe documentos requeridos que no fueron aportados.

    Eso debe producir DOCUMENTOS_FALTANTES, no REVISION_HUMANA.
    """
    text = normal(value)

    patterns = (
        'no se han adjuntado',
        'no se adjuntaron',
        'no fue aportado',
        'no fueron aportados',
        'documento faltante',
        'documentos faltantes',
        'falta el documento',
        'faltan los documentos',
        'no se encontro el documento requerido',
        'no se encontraron los documentos requeridos',
    )

    return any(
        pattern in text
        for pattern in patterns
    )


def evidence_valid(evidence: Evidence, docs: dict[str, Document], allowed=None):
    doc = docs.get(evidence.document)
    return bool(doc and (allowed is None or evidence.document in allowed)
                and 1 <= evidence.page <= len(doc.pages)
                and normal(evidence.quote) in normal(doc.pages[evidence.page - 1])
                and len(normal(evidence.quote)) >= 5)


def references_valid(items, docs, allowed=None):
    return bool(items) and all(evidence_valid(e, docs, allowed) for e in items)


def fact_valid(fact: Fact, docs, allowed, kind='text'):
    if not fact.value or not references_valid(fact.evidence, docs, allowed):
        return False
    text = ' '.join(e.quote for e in fact.evidence)
    if kind == 'date':
        try:
            d = date.fromisoformat(fact.value)
        except ValueError:
            return False
        candidates = [d.isoformat(), f'{d.day}/{d.month}/{d.year}', f'{d.day:02}/{d.month:02}/{d.year}',
                      f'{d.day:02}-{d.month:02}-{d.year}', f'{d.day}-{d.month}-{d.year}']
        months = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
        candidates += [f'{d.day} de {months[d.month-1]} de {d.year}', f'{d.day:02} de {months[d.month-1]} de {d.year}']
        return any(normal(c) in normal(text) for c in candidates)
    if kind == 'number':
        return fact.value.isdigit() and bool(re.search(r'(?<!\d)' + re.escape(fact.value) + r'(?!\d)', text))
    return bool(compact(fact.value)) and compact(fact.value) in compact(text)


def evaluate(data: Extraction, documents: list[Document]):
    docs = {d.id: d for d in documents}
    policy = {'poliza'}
    clinical = set(docs) - policy
    checks, missing, uncertainties = [], [], list(data.uncertainties)

    def add(name, status, detail, evidence=()):
        checks.append({'name': name, 'status': status, 'detail': detail,
                       'evidence': [e.model_dump() | {'verified': evidence_valid(e, docs)} for e in evidence]})

    def known(fact, roles, kind='text'):
        return fact_valid(fact, docs, roles, kind)

    # Una cita inexistente en cualquier campo bloquea la preaprobación.
    def audit(value):
        if isinstance(value, dict):
            if set(value) == {'document', 'page', 'quote'}:
                if not evidence_valid(Evidence(**value), docs):
                    uncertainties.append('Hay una cita que no coincide con el documento y la página indicados.')
            else:
                for v in value.values():
                    audit(v)
        elif isinstance(value, list):
            for v in value:
                audit(v)
    audit(data.model_dump())
    if data.patient_name.value is not None and not known(data.patient_name, clinical):
        uncertainties.append('El nombre del paciente extraído no está respaldado por su cita.')

    if known(data.insured_id, policy) and known(data.patient_id, clinical):
        same = compact(data.insured_id.value) == compact(data.patient_id.value)
        add('Identidad del asegurado', 'pass' if same else 'review',
            'El identificador del paciente coincide con el asegurado.' if same else
            'Los identificadores no coinciden. Verifica que la póliza corresponda al paciente.',
            data.insured_id.evidence + data.patient_id.evidence)
    else:
        add('Identidad del asegurado', 'missing', 'Falta un identificador verificable del asegurado o del paciente.')
        missing.append('Identificación del mismo paciente en la póliza y en el informe.')

    if not known(data.policy_number, policy):
        add('Número de póliza', 'missing', 'No se pudo verificar el número de póliza.')
        missing.append('Póliza con su número identificador.')
    elif data.report_policy_number.value is not None:
        ok = known(data.report_policy_number, clinical) and compact(data.policy_number.value) == compact(data.report_policy_number.value)
        add('Número de póliza', 'pass' if ok else 'review', 'Número de póliza coincidente.' if ok else
            'El número de póliza indicado en la solicitud no coincide o no tiene evidencia verificable.',
            data.policy_number.evidence + data.report_policy_number.evidence)
    else:
        add('Número de póliza', 'pass', f'Póliza identificada: {data.policy_number.value}.', data.policy_number.evidence)

    dates_valid = known(data.coverage_start, policy, 'date') and known(data.coverage_end, policy, 'date') and known(data.surgery_date, clinical, 'date')
    start = end = surgery = None
    if dates_valid:
        start, end, surgery = [date.fromisoformat(x.value) for x in (data.coverage_start, data.coverage_end, data.surgery_date)]
        if start > end:
            add('Vigencia', 'review', 'El inicio de cobertura es posterior a su vencimiento.')
            dates_valid = False
        else:
            valid = start <= surgery <= end
            add('Vigencia', 'pass' if valid else 'fail',
                f'Cirugía: {surgery.isoformat()}. Cobertura: {start.isoformat()} a {end.isoformat()}.',
                data.coverage_start.evidence + data.coverage_end.evidence + data.surgery_date.evidence)
    else:
        add('Vigencia', 'missing', 'No se verificaron todas las fechas: inicio de cobertura, vencimiento y cirugía.')
        missing.append('Fechas explícitas de cobertura del asegurado y de la cirugía solicitada.')

    coverage_proof = references_valid(data.coverage_evidence, docs, policy)
    procedures_known = known(data.covered_procedure, policy) and known(data.requested_procedure, clinical)
    if data.coverage_status == 'excluded' and coverage_proof:
        add('Cobertura del procedimiento', 'fail', 'Se identificó una exclusión expresa aplicable. Requiere confirmación de la aseguradora.', data.coverage_evidence)
    elif data.coverage_status == 'covered' and coverage_proof and procedures_known:
        same = compact(data.covered_procedure.value) == compact(data.requested_procedure.value)
        add('Cobertura del procedimiento', 'pass' if same else 'review',
            f'Cobertura expresa para {data.covered_procedure.value}.' if same else
            'Los nombres del procedimiento difieren entre informe y póliza. Confirma la equivalencia; el sistema no la presupone.',
            data.coverage_evidence + data.requested_procedure.evidence)
    else:
        add('Cobertura del procedimiento', 'review', 'No hay evidencia suficiente de cobertura expresa para el procedimiento solicitado.', data.coverage_evidence)

    waiting_info = None
    if dates_valid and known(data.waiting_days, policy, 'number'):
        days = int(data.waiting_days.value)
        if days <= 36500 and start <= date.max - timedelta(days=days):
            elapsed = (surgery - start).days
            eligible = start + timedelta(days=days)
            waiting_info = {'required_days': days, 'elapsed_days': elapsed,
                            'remaining_days': max(0, days - elapsed), 'eligible_date': eligible.isoformat()}
            add('Período de carencia', 'pass' if elapsed >= days else 'fail',
                f'{elapsed} días transcurridos de {days} requeridos. Carencia cumplida a partir del {eligible.isoformat()}.', data.waiting_days.evidence)
        else:
            add('Período de carencia', 'review', 'El plazo extraído es inusual y necesita revisión.')
    else:
        add('Período de carencia', 'review', 'No se pudo calcular la carencia con fechas verificadas y un plazo explícito en días.', data.waiting_days.evidence)

    if not data.requirements_known or not references_valid(data.requirements_evidence, docs, policy):
        add('Requisitos documentales', 'review', 'No se identificó una lista completa y verificable de requisitos en la póliza.')
    elif not data.documents:
        clause = normal(' '.join(e.quote for e in data.requirements_evidence))
        explicit_none = any(term in clause for term in (
            'no se requieren documentos adicionales', 'sin requisitos documentales adicionales',
            'no se exige documentacion adicional', 'no se requieren otros documentos'))
        add('Requisitos documentales', 'pass' if explicit_none else 'review',
            'La póliza declara expresamente que no exige documentos adicionales.' if explicit_none else
            'La extracción no enumeró documentos y no se verificó una cláusula que los dispense.', data.requirements_evidence)
    for requirement in data.documents:
        if not references_valid(requirement.policy_evidence, docs, policy):
            add(requirement.name, 'review', 'El requisito no está respaldado por una cláusula verificable.', requirement.policy_evidence)
        elif requirement.present is True and references_valid(requirement.evidence, docs, clinical):
            add(requirement.name, 'pass', 'Documento aportado con contenido verificable.', requirement.policy_evidence + requirement.evidence)
        elif requirement.present is False:
            add(requirement.name, 'missing', 'No se encontró el documento requerido entre los archivos aportados.', requirement.policy_evidence)
            missing.append(requirement.name)
        else:
            add(requirement.name, 'review', 'No se pudo confirmar que el documento esté aportado y completo.', requirement.policy_evidence + requirement.evidence)

    for condition in data.additional_conditions:
        good = (
            references_valid(
                condition.policy_evidence,
                docs,
                policy
            )
            and references_valid(
                condition.evidence,
                docs,
                clinical
            )
        )

        state = (
            'pass'
            if condition.fulfilled is True and good
            else 'fail'
            if condition.fulfilled is False and good
            else 'review'
        )

        add(
            condition.name,
            state,
            (
                'Condición adicional cumplida.'
                if state == 'pass'
                else 'Condición adicional no cumplida.'
                if state == 'fail'
                else 'Condición adicional que requiere revisión.'
            ),
            condition.policy_evidence
            + condition.evidence
        )

    # Eliminar duplicados y separar incertidumbres reales
    # de simples documentos faltantes.
    uncertainties = list(
        dict.fromkeys(
            uncertainty
            for uncertainty in uncertainties
            if not is_missing_document_uncertainty(
                uncertainty
            )
        )
    )

    # Solo una incertidumbre real provoca revisión humana.
    for uncertainty in uncertainties:
        add(
            'Revisión de la extracción',
            'review',
            uncertainty
        )

    states = {
        check['status']
        for check in checks
    }

    if 'review' in states:
        status = 'REVISION_HUMANA'
        title = 'Requiere revisión humana'

        summary = (
            'Hay información ambigua, contradictoria '
            'o sin evidencia suficiente. '
            'No se emitió una preaprobación.'
        )

    elif 'fail' in states:
        status = 'NO_PREAPROBADA'
        title = 'No procede la preaprobación automática'

        summary = (
            'Una o más condiciones no se cumplen para '
            'la fecha solicitada. El resultado es '
            'preliminar y no constituye una denegación '
            'definitiva.'
        )

    elif 'missing' in states:
        status = 'DOCUMENTOS_FALTANTES'
        title = 'Documentos faltantes'
        summary = (
            'Faltan documentos requeridos para completar '
            'la preautorización.'
    )
    else:
        status = 'PREAPROBADO'
        title = 'Preaprobación preliminar'
        summary = (
            'Las comprobaciones implementadas se cumplen '
            'según los documentos aportados. '
            'Sujeto a validación de la aseguradora.'
        )

    return {
        'status': status,
        'title': title,
        'summary': summary,
        'checks': checks,
        'missing_documents': list(
            dict.fromkeys(missing)
        ),
        'uncertainties': uncertainties,
        'waiting': waiting_info,
        'disclaimer': (
            'Prototipo de demostración. '
            'No emite autorizaciones definitivas '
            'ni recomendaciones médicas.'
        ),
    }
