from __future__ import annotations

import unittest

from entity_store_transformation_client.models.tender_process_status import (
    TenderProcessStatus,
)

from services.entity_store_submission_service import EntityStoreSubmissionService


class FakeMetadataStore:
    def __init__(self) -> None:
        self.files = {
            ('tender-1', 'tender-1/architectural/a101.pdf'): {
                'id': 'file-1',
                'name': 'a101.pdf',
                'path': 'tender-1/architectural/a101.pdf',
                'batch_id': 'batch-1',
                'submitted_at': '2026-03-12T10:00:00',
                'updated_at': '2026-03-12T10:00:00',
                'extraction_status': '',
                'provider': '',
                'drawing_number': '',
                'drawing_revision': '',
                'revision_date': '',
                'drawing_title': '',
                'transaction_id': '',
                'destination_path': '',
                'last_error': '',
                'extracted_at': '',
                'extraction_reference': '',
            }
        }
        self.batch_context = {
            'tender_id': 'tender-1',
            'batch': {
                'batch_id': 'batch-1',
                'status': 'running',
                'submitted_at': '2026-03-12T10:00:00',
                'submission_attempts': [
                    {
                        'timestamp': '2026-03-12T10:00:00',
                        'started_at': '2026-03-12T10:00:00',
                        'completed_at': '2026-03-12T10:01:00',
                        'duration_seconds': 60,
                        'status': 'success',
                    }
                ],
                'completed_at': '',
                'uipath_reference': 'batch-batch-1',
            },
        }

    def get_file(self, tender_id: str, file_path: str):
        return dict(self.files[(tender_id, file_path)])

    def update_file_metadata(self, tender_id: str, file_path: str, metadata):
        record = self.files[(tender_id, file_path)]
        for key, value in metadata.items():
            record[key] = value
        record['updated_at'] = '2026-03-12T10:05:00'
        return dict(record)

    def get_batch_by_reference(self, reference: str):
        if reference == self.batch_context['batch']['uipath_reference']:
            return self.batch_context
        return None

    def get_batch_files(self, tender_id: str, batch_id: str):
        return [
            dict(record)
            for (record_tender_id, _), record in self.files.items()
            if record_tender_id == tender_id and record.get('batch_id') == batch_id
        ]


class EntityStoreSubmissionServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.metadata_store = FakeMetadataStore()
        self.service = EntityStoreSubmissionService(self.metadata_store)

    def test_ensure_submission_records_initializes_cosmos_extraction_state(self) -> None:
        context = self.service.ensure_submission_records(
            tender_id='tender-1',
            file_paths=['tender-1/architectural/a101.pdf'],
            submitted_by='user@example.com',
            reference='batch-batch-1',
        )

        stored_file = context.files_by_path['tender-1/architectural/a101.pdf']
        self.assertEqual(context.reference, 'batch-batch-1')
        self.assertEqual(context.submission_id, 'batch-1')
        self.assertEqual(context.project_id, 'tender-1')
        self.assertEqual(stored_file.status, TenderProcessStatus.QUEUED)
        self.assertEqual(stored_file.provider, 'internal')
        self.assertEqual(
            self.metadata_store.files[('tender-1', 'tender-1/architectural/a101.pdf')]['extraction_reference'],
            'batch-batch-1',
        )

    def test_ensure_submission_records_resets_when_reference_changes(self) -> None:
        self.metadata_store.files[('tender-1', 'tender-1/architectural/a101.pdf')].update(
            {
                'extraction_status': 'extracted',
                'drawing_number': 'A-101',
                'drawing_revision': 'B',
                'revision_date': '2026-03-12',
                'drawing_title': 'Ground Floor Plan',
                'extraction_reference': 'batch-old',
            }
        )

        context = self.service.ensure_submission_records(
            tender_id='tender-1',
            file_paths=['tender-1/architectural/a101.pdf'],
            submitted_by='user@example.com',
            reference='batch-batch-1',
        )

        stored_file = context.files_by_path['tender-1/architectural/a101.pdf']
        self.assertEqual(stored_file.status, TenderProcessStatus.QUEUED)
        self.assertIsNone(stored_file.drawing_number)
        self.assertIsNone(stored_file.drawing_revision)
        self.assertIsNone(stored_file.revision_date)
        self.assertIsNone(stored_file.drawing_title)

    def test_get_batch_progress_aggregates_from_batch_files(self) -> None:
        self.metadata_store.files[('tender-1', 'tender-1/architectural/a101.pdf')].update(
            {
                'extraction_status': 'extracted',
                'provider': 'internal',
                'drawing_number': 'A-101',
                'drawing_revision': 'B',
                'revision_date': '2026-03-12',
                'drawing_title': 'Ground Floor Plan',
                'extracted_at': '2026-03-12T10:06:00',
                'extraction_reference': 'batch-batch-1',
            }
        )

        progress = self.service.get_batch_progress('batch-batch-1')

        self.assertEqual(progress['total_files'], 1)
        self.assertEqual(progress['status_counts']['extracted'], 1)
        self.assertEqual(progress['status_counts']['queued'], 0)
        self.assertEqual(progress['files'][0]['drawing_number'], 'A-101')
        self.assertEqual(progress['files'][0]['revision_date'], '2026-03-12')
        self.assertEqual(progress['metrics']['submission']['duration_seconds'], 60)
        self.assertEqual(progress['metrics']['submission']['source'], 'exact')
        self.assertEqual(progress['metrics']['extraction']['source'], 'estimated')
        self.assertEqual(progress['metrics']['throughput']['processed_files'], 1)


if __name__ == '__main__':
    unittest.main()
