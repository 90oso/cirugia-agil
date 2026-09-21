import asyncio
from dataclasses import replace
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.ai import AIError, extract
from app.config import Settings
from app.documents import DocumentError, extract_document
from app.main import create_app
from app.rules import evaluate
from app.notion import Notion
from app.storage import Store
from fixtures import example
from fake_ollama import FakeOllama


class RuleTests(unittest.TestCase):
    def test_complete_case_is_preapproved(self):
        docs, facts = example()
        result = evaluate(facts, docs)
        self.assertEqual(result['status'], 'PREAPROBADA')
        self.assertEqual(result['waiting']['elapsed_days'], 212)
        self.assertTrue(all(c['status'] == 'pass' for c in result['checks']))

    def test_missing_order_requests_document(self):
        docs, facts = example(order=False)
        result = evaluate(facts, docs)
        self.assertEqual(result['status'], 'DOCUMENTOS_PENDIENTES')
        self.assertEqual(result['missing_documents'], ['Orden quirúrgica'])

    def test_waiting_boundary_is_exact(self):
        for elapsed, expected in [(179, 'NO_PREAPROBADA'), (180, 'PREAPROBADA'), (181, 'PREAPROBADA')]:
            with self.subTest(elapsed=elapsed):
                surgery = (date(2026, 1, 1) + timedelta(days=elapsed)).isoformat()
                docs, facts = example(surgery=surgery)
                result = evaluate(facts, docs)
                self.assertEqual(result['status'], expected)
                self.assertEqual(result['waiting']['eligible_date'], '2026-06-30')

    def test_expired_policy(self):
        docs, facts = example(surgery='2027-01-01')
        self.assertEqual(evaluate(facts, docs)['status'], 'NO_PREAPROBADA')

    def test_fabricated_citation_blocks_approval(self):
        docs, facts = example()
        facts.coverage_evidence[0].quote = 'Esto nunca aparece en la póliza'
        self.assertEqual(evaluate(facts, docs)['status'], 'REVISION_HUMANA')

    def test_wrong_page_blocks_approval(self):
        docs, facts = example()
        facts.coverage_evidence[0].page = 2
        self.assertEqual(evaluate(facts, docs)['status'], 'REVISION_HUMANA')

    def test_value_must_be_in_evidence(self):
        docs, facts = example()
        facts.waiting_days.value = '0'
        self.assertEqual(evaluate(facts, docs)['status'], 'REVISION_HUMANA')

    def test_different_patient(self):
        docs, facts = example()
        docs[1].pages[0] = docs[1].pages[0].replace('ID-01', 'ID-02')
        facts.patient_id.value = 'ID-02'
        facts.patient_id.evidence[0].quote = 'ID-02'
        self.assertEqual(evaluate(facts, docs)['status'], 'REVISION_HUMANA')

    def test_unknown_requirements(self):
        docs, facts = example()
        facts.requirements_known = False
        self.assertEqual(evaluate(facts, docs)['status'], 'REVISION_HUMANA')

    def test_omitted_document_list_is_not_a_blanket_approval(self):
        docs, facts = example()
        facts.documents = []
        self.assertEqual(evaluate(facts, docs)['status'], 'REVISION_HUMANA')

    def test_explicit_exclusion(self):
        docs, facts = example()
        docs[0].pages[0] = docs[0].pages[0].replace('Procedimiento cubierto:', 'Procedimiento excluido:')
        facts.coverage_status = 'excluded'
        facts.coverage_evidence[0].quote = 'Procedimiento excluido: Reparación de hernia.'
        self.assertEqual(evaluate(facts, docs)['status'], 'NO_PREAPROBADA')

    def test_unresolved_condition(self):
        docs, facts = example()
        facts.uncertainties.append('Falta confirmar una exclusión de la póliza.')
        self.assertEqual(evaluate(facts, docs)['status'], 'REVISION_HUMANA')

    def test_procedure_synonym_requires_review(self):
        docs, facts = example()
        docs[1].pages[0] = docs[1].pages[0].replace('Procedimiento solicitado: Reparación de hernia.', 'Procedimiento solicitado: Hernioplastia.')
        facts.requested_procedure.value = 'Hernioplastia'
        facts.requested_procedure.evidence[0].quote = 'Hernioplastia'
        self.assertEqual(evaluate(facts, docs)['status'], 'REVISION_HUMANA')

    def test_blank_scanned_pdf_is_not_silently_omitted(self):
        pdf = PdfWriter(); pdf.add_blank_page(width=300, height=400)
        content = BytesIO(); pdf.write(content)
        with self.assertRaisesRegex(DocumentError, 'OCR'):
            extract_document('poliza', 'escaneado.pdf', content.getvalue())

    def test_too_long_documents_never_reach_model(self):
        docs, _ = example()
        cfg = replace(Settings(), max_chars=10)
        with self.assertRaisesRegex(AIError, 'No se ha recortado'):
            asyncio.run(extract(cfg, 'test-model', docs))


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs, facts = example()
        cls.fake = FakeOllama(facts).start()
        cls.temp = tempfile.TemporaryDirectory()
        cls.cfg = replace(Settings(), ollama_url=cls.fake.url, data_dir=Path(cls.temp.name),
                          notion_token='', notion_data_source='', timeout=10)
        cls.client = TestClient(create_app(cls.cfg))

    @classmethod
    def tearDownClass(cls):
        cls.client.close(); cls.fake.stop(); cls.temp.cleanup()

    def send(self, docs=None):
        docs = docs or self.docs
        return self.client.post('/api/analyze', data={'model': 'test-local:latest'}, files={
            'policy': ('poliza.txt', docs[0].content, 'text/plain'),
            'report': ('informe.txt', docs[1].content, 'text/plain')})

    def test_form_is_served_without_external_scripts(self):
        result = self.client.get('/')
        self.assertEqual(result.status_code, 200)
        self.assertIn('Evaluar solicitud', result.text)
        self.assertIn("frame-ancestors 'none'", result.headers['Content-Security-Policy'])

    def test_health_filters_cloud_models(self):
        data = self.client.get('/api/health').json()
        self.assertTrue(data['ollama_connected'])
        self.assertEqual(data['models'], ['test-local:latest'])

    def test_model_probe_calls_real_http_boundary(self):
        response = self.client.post('/api/model/test', json={'model': 'test-local:latest'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])

    def test_upload_extract_evaluate_save_export(self):
        response = self.send()
        self.assertEqual(response.status_code, 200, response.text)
        case = response.json()
        self.assertEqual(case['status'], 'PREAPROBADA')
        self.assertEqual(case['extraction']['patient_name']['value'], 'Ana Ejemplo')
        request = self.fake.requests[-1]
        self.assertFalse(request['stream'])
        self.assertIn('coverage_start', request['format']['properties'])
        self.assertIn('[DOCUMENTO poliza | PÁGINA 1]', request['messages'][1]['content'])
        self.assertEqual(self.client.get('/api/cases/' + case['id']).json()['status'], 'PREAPROBADA')
        self.assertTrue(self.client.get('/api/cases').json())
        exported = self.client.get('/api/cases/' + case['id'] + '/export')
        self.assertIn('attachment;', exported.headers['Content-Disposition'])
        self.assertNotIn('disk_name', exported.json()['documents'][0])
        original = self.client.get('/api/cases/' + case['id'] + '/documents/poliza')
        self.assertEqual(original.content, self.docs[0].content)
        # Persistencia real, abriendo una nueva conexión de almacenamiento.
        self.assertEqual(Store(self.cfg).get(case['id'])['status'], 'PREAPROBADA')

    def test_missing_and_waiting_scenarios_through_http(self):
        for args, expected in [({'order': False}, 'DOCUMENTOS_PENDIENTES'), ({'surgery': '2026-04-01'}, 'NO_PREAPROBADA')]:
            with self.subTest(args=args):
                docs, facts = example(**args)
                self.fake.extraction = facts
                response = self.send(docs)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()['status'], expected)
        self.fake.extraction = example()[1]

    def test_invalid_file_and_large_file(self):
        response = self.client.post('/api/analyze', data={'model': 'test-local:latest'}, files={
            'policy': ('p.exe', b'not-a-document'), 'report': ('r.txt', b'text')})
        self.assertEqual(response.status_code, 422)
        response = self.client.post('/api/analyze', data={'model': 'test-local:latest'}, files={
            'policy': ('p.txt', b'a' * (5 * 1024 * 1024 + 1)), 'report': ('r.txt', b'text')})
        self.assertEqual(response.status_code, 413)

    def test_invalid_model_output_creates_no_case(self):
        before = len(self.client.get('/api/cases').json())
        call_count = len(self.fake.requests)
        self.fake.invalid_response = True
        try:
            response = self.send()
            self.assertEqual(response.status_code, 503)
            self.assertEqual(len(self.fake.requests) - call_count, 2)
            self.assertEqual(len(self.client.get('/api/cases').json()), before)
        finally:
            self.fake.invalid_response = False

    def test_notion_does_not_send_without_configuration(self):
        case = self.send().json()
        response = self.client.post('/api/cases/' + case['id'] + '/notion')
        self.assertEqual(response.status_code, 502)
        self.assertIn('Configura', response.json()['detail'])

    def test_cross_origin_mutation_is_rejected(self):
        response = self.client.post('/api/model/test', json={'model': 'test-local:latest'}, headers={'Origin': 'https://untrusted.example'})
        self.assertEqual(response.status_code, 403)

    def test_malicious_host_is_rejected(self):
        response = self.client.get('/api/cases', headers={'Host': 'untrusted.example'})
        self.assertEqual(response.status_code, 400)

    def test_notion_payload_uses_data_source_and_attaches_originals(self):
        case = self.send().json()
        cfg = replace(self.cfg, notion_token='test-secret', notion_data_source='test-data-source')
        notion = Notion(cfg)
        uploaded = []
        async def fake_upload(path, filename, mime):
            uploaded.append((path, filename, mime))
            return {'object': 'block', 'type': 'file', 'file': {'type': 'file_upload', 'file_upload': {'id': 'upload-test'}, 'name': filename}}
        calls = []
        async def fake_call(method, path, **kwargs):
            calls.append((method, path, kwargs))
            if path.startswith('/data_sources'):
                return {'properties': {'Solicitud': {'type': 'title'}}}
            if path == '/pages':
                return {'id': 'page-test', 'url': 'https://www.notion.so/page-test'}
            raise AssertionError(path)
        notion.call = fake_call; notion.upload = fake_upload
        store = Store(self.cfg)
        first = asyncio.run(notion.sync(case, store))
        self.assertEqual(len(uploaded), 2)
        self.assertEqual(calls[-1][2]['json']['parent']['data_source_id'], 'test-data-source')
        second = asyncio.run(notion.sync(store.get(case['id']), store))
        self.assertEqual(first, second)
        self.assertEqual(len(uploaded), 2, 'No debe duplicar páginas al volver a guardar una solicitud sincronizada.')


if __name__ == '__main__':
    unittest.main()
