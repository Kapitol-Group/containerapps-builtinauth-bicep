from __future__ import annotations

import json
import unittest
from types import SimpleNamespace
from uuid import uuid4

import fitz

from entity_store_transformation_client.models.tender_file import TenderFile
from entity_store_transformation_client.models.tender_process_status import (
    TenderProcessStatus,
)
from entity_store_transformation_client.models.tender_project import TenderProject
from entity_store_transformation_client.models.tender_submission import TenderSubmission
from entity_store_transformation_client.models.title_block_validation_users import (
    TitleBlockValidationUsers,
)
from services.entity_store_submission_service import SubmissionContext
from services.internal_extraction_worker import InternalExtractionWorker
from services.extraction_queue import ExtractionBatchMessage
from services.vision_extractor import (
    RetryableVisionError,
    TitleBlockExtractionSchema,
    VisionExtractionResult,
)


def _build_pdf() -> bytes:
    document = fitz.open()
    try:
        page = document.new_page(width=500, height=300)
        page.insert_text((360, 250), "A-101", fontsize=18)
        page.insert_text((360, 270), "Ground Floor Plan", fontsize=12)
        return document.tobytes()
    finally:
        document.close()


def _build_tender_file(path: str, status: TenderProcessStatus) -> TenderFile:
    project = TenderProject(name="Tender A", id=uuid4())
    user = TitleBlockValidationUsers(
        user_email="user@example.com",
        id=uuid4(),
    )
    submission = TenderSubmission(
        project_id=project,
        reference="batch-batch-1",
        submitted_by=user,
        validated_by=user,
        archive_name="n/a",
        is_addendum=False,
        id=uuid4(),
    )
    return TenderFile(
        submission_id=submission,
        original_path=path,
        original_filename=path.split('/')[-1],
        provider='internal',
        status=status,
        id=uuid4(),
    )


class FakeMetadataStore:
    def __init__(self, batch):
        self.batch = dict(batch)

    def get_batch(self, tender_id, batch_id):
        if self.batch['batch_id'] == batch_id and self.batch['tender_id'] == tender_id:
            return dict(self.batch)
        return None

    def update_batch(self, tender_id, batch_id, updates):
        if self.batch['batch_id'] != batch_id or self.batch['tender_id'] != tender_id:
            return None
        self.batch.update(updates)
        return dict(self.batch)


class FakeBlobService:
    def __init__(self, pdf_bytes):
        self.pdf_bytes = pdf_bytes
        self.uploads = []

    def download_file(self, tender_id, file_path):
        return {
            'content': self.pdf_bytes,
            'filename': file_path.split('/')[-1],
            'content_type': 'application/pdf',
        }

    def upload_bytes(self, blob_name, payload, *, content_type='application/octet-stream', metadata=None):
        self.uploads.append((blob_name, content_type, len(payload)))
        return {'path': blob_name}


class FakeSubmissionStore:
    def __init__(self, files_by_path):
        self.files_by_path = files_by_path

    def ensure_submission_records(self, **kwargs):
        submission = next(iter(self.files_by_path.values())).submission_id
        return SubmissionContext(
            reference=kwargs['reference'],
            submission_id=str(submission.id),
            project_id=str(submission.project_id.id),
            files_by_path=self.files_by_path,
        )

    def mark_tender_file_extracted(self, tender_file, **kwargs):
        tender_file.status = TenderProcessStatus.EXTRACTED
        tender_file.drawing_number = kwargs['drawing_number']
        tender_file.drawing_revision = kwargs['drawing_revision']
        tender_file.drawing_title = kwargs['drawing_title']
        tender_file.transaction_id = kwargs.get('transaction_id')
        return tender_file

    def mark_tender_file_failed(self, tender_file, **kwargs):
        tender_file.status = TenderProcessStatus.FAILED
        tender_file.transaction_id = kwargs.get('transaction_id')
        tender_file.drawing_number = None
        tender_file.drawing_revision = None
        tender_file.drawing_title = None
        return tender_file

    def get_batch_progress(self, reference):
        counts = {'queued': 0, 'extracted': 0, 'failed': 0, 'exported': 0}
        for tender_file in self.files_by_path.values():
            if tender_file.status == TenderProcessStatus.EXTRACTED:
                counts['extracted'] += 1
            elif tender_file.status == TenderProcessStatus.FAILED:
                counts['failed'] += 1
            elif tender_file.status == TenderProcessStatus.EXPORTED:
                counts['exported'] += 1
            else:
                counts['queued'] += 1
        return {'total_files': len(self.files_by_path), 'status_counts': counts, 'files': []}


class FakeQueueService:
    def __init__(self):
        self.deleted_messages = []

    def delete_message(self, message):
        self.deleted_messages.append(message)


class FakeTelemetry:
    def record_dequeue(self, **kwargs):
        return None

    def record_file_latency(self, **kwargs):
        return None

    def record_model_failure(self, **kwargs):
        return None

    def record_token_usage(self, **kwargs):
        return None

    def record_batch_completion(self, **kwargs):
        return None


class FakeVisionExtractor:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def extract_title_block(self, **kwargs):
        self.calls += 1
        response = self.responses[min(self.calls - 1, len(self.responses) - 1)]
        if isinstance(response, Exception):
            raise response
        return response


class InternalExtractionWorkerTests(unittest.TestCase):
    def _build_worker(self, *, tender_file, vision_responses):
        batch = {
            'tender_id': 'tender-1',
            'batch_id': 'batch-1',
            'file_paths': [tender_file.original_path],
            'title_block_coords': {'x': 320, 'y': 200, 'width': 140, 'height': 90},
            'submitted_by': 'user@example.com',
            'sharepoint_folder_path': '',
            'output_folder_path': '',
            'folder_list': [],
            'status': 'running',
            'last_error': '',
        }
        metadata_store = FakeMetadataStore(batch)
        blob_service = FakeBlobService(_build_pdf())
        submission_store = FakeSubmissionStore({tender_file.original_path: tender_file})
        queue_service = FakeQueueService()
        worker = InternalExtractionWorker(
            metadata_store=metadata_store,
            blob_service=blob_service,
            submission_store=submission_store,
            queue_service=queue_service,
            vision_extractor=FakeVisionExtractor(vision_responses),
            telemetry=FakeTelemetry(),
            render_dpi=300,
            max_dequeue_count=3,
            visibility_timeout_seconds=600,
            poll_interval_seconds=1,
        )
        return worker, metadata_store, blob_service, submission_store, queue_service

    def test_duplicate_message_does_not_reprocess_completed_file(self) -> None:
        tender_file = _build_tender_file('tender-1/architectural/a101.pdf', TenderProcessStatus.QUEUED)
        response = VisionExtractionResult(
            extraction=TitleBlockExtractionSchema(
                drawing_number='A-101',
                drawing_revision='B',
                drawing_title='Ground Floor Plan',
            ),
            raw_response_json=json.dumps({'ok': True}),
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        )
        worker, metadata_store, blob_service, _, queue_service = self._build_worker(
            tender_file=tender_file,
            vision_responses=[response],
        )

        queue_message = SimpleNamespace(
            content=ExtractionBatchMessage(
                tender_id='tender-1',
                batch_id='batch-1',
                reference='batch-batch-1',
            ).to_json(),
            dequeue_count=1,
        )

        worker.handle_queue_message(queue_message)
        worker.handle_queue_message(queue_message)

        self.assertEqual(tender_file.status, TenderProcessStatus.EXTRACTED)
        self.assertEqual(worker.vision_extractor.calls, 1)
        self.assertEqual(metadata_store.batch['status'], 'completed')
        self.assertTrue(metadata_store.batch.get('completed_at'))
        self.assertEqual(len(blob_service.uploads), 2)
        self.assertEqual(len(queue_service.deleted_messages), 2)

    def test_max_dequeue_count_hard_fails_remaining_files(self) -> None:
        tender_file = _build_tender_file('tender-1/architectural/a101.pdf', TenderProcessStatus.QUEUED)
        worker, metadata_store, _, _, queue_service = self._build_worker(
            tender_file=tender_file,
            vision_responses=[RetryableVisionError("transient openai outage")],
        )

        queue_message = SimpleNamespace(
            content=ExtractionBatchMessage(
                tender_id='tender-1',
                batch_id='batch-1',
                reference='batch-batch-1',
            ).to_json(),
            dequeue_count=3,
        )

        worker.handle_queue_message(queue_message)

        self.assertEqual(tender_file.status, TenderProcessStatus.FAILED)
        self.assertEqual(metadata_store.batch['status'], 'failed')
        self.assertTrue(metadata_store.batch.get('completed_at'))
        self.assertEqual(metadata_store.batch['last_error'], 'transient openai outage')
        self.assertEqual(len(queue_service.deleted_messages), 1)


if __name__ == '__main__':
    unittest.main()
