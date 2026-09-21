"""Datos unitarios sintéticos; no son documentos de entrega ni resultados de un modelo real."""
from app.documents import extract_document
from app.models import Extraction


def example(surgery='2026-08-01', order=True):
    policy = ('Póliza DEMO-100. Asegurado ID-01. Inicio de cobertura continua: 2026-01-01. '
              'Fin de cobertura: 2026-12-31. Procedimiento cubierto: Reparación de hernia. '
              'Carencia: 180 días. Requisitos únicos: informe médico y orden quirúrgica. '
              'Sin condiciones adicionales.')
    report = (f'Paciente Ana Ejemplo. Identificador ID-01. Póliza DEMO-100. '
              f'Procedimiento solicitado: Reparación de hernia. Cirugía programada: {surgery}. '
              'INFORME MÉDICO: solicitud sintética para prueba de software.')
    if order:
        report += ' ORDEN QUIRÚRGICA: Reparación de hernia. Firma: Profesional ficticio.'
    docs = [extract_document('poliza', 'poliza.txt', policy.encode()),
            extract_document('informe', 'informe.txt', report.encode())]

    def ev(text, role='poliza'):
        return {'document': role, 'page': 1, 'quote': text}

    def fact(value, role='poliza', quote=None):
        return {'value': value, 'evidence': [ev(quote or value, role)] if value is not None else []}

    extraction = {
        'policy_number': fact('DEMO-100'), 'insured_id': fact('ID-01'),
        'coverage_start': fact('2026-01-01'), 'coverage_end': fact('2026-12-31'),
        'waiting_days': fact('180', quote='Carencia: 180 días.'),
        'covered_procedure': fact('Reparación de hernia'), 'coverage_status': 'covered',
        'coverage_evidence': [ev('Procedimiento cubierto: Reparación de hernia.')],
        'patient_name': fact('Ana Ejemplo', 'informe'), 'patient_id': fact('ID-01', 'informe'),
        'report_policy_number': fact('DEMO-100', 'informe'),
        'surgery_date': fact(surgery, 'informe'), 'requested_procedure': fact('Reparación de hernia', 'informe'),
        'requirements_known': True,
        'requirements_evidence': [ev('Requisitos únicos: informe médico y orden quirúrgica.')],
        'documents': [
            {'name': 'Informe médico', 'policy_evidence': [ev('Requisitos únicos: informe médico y orden quirúrgica.')],
             'present': True, 'evidence': [ev('INFORME MÉDICO: solicitud sintética para prueba de software.', 'informe')]},
            {'name': 'Orden quirúrgica', 'policy_evidence': [ev('Requisitos únicos: informe médico y orden quirúrgica.')],
             'present': order, 'evidence': [ev('ORDEN QUIRÚRGICA: Reparación de hernia. Firma: Profesional ficticio.', 'informe')] if order else []}
        ], 'additional_conditions': [], 'uncertainties': []
    }
    return docs, Extraction.model_validate(extraction)
