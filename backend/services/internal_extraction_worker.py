from __future__ import annotations

import logging
import os
import time
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from datetime import UTC, datetime
from typing import Dict, List

from entity_store_transformation_client.models.tender_process_status import (
    TenderProcessStatus,
)

from services.blob_storage import BlobStorageService
from services.entity_store_submission_service import EntityStoreSubmissionService
from services.extraction_queue import ExtractionBatchMessage, ExtractionQueueService
from services.extraction_telemetry import ExtractionTelemetry
from services.metadata_store import MetadataStore
from services.title_block_renderer import render_title_block_region
from services.vision_extractor import (
    RetryableVisionError,
    VisionExtractor,
    VisionExtractorError,
    extraction_has_values,
)

logger = logging.getLogger(__name__)

TERMINAL_FILE_STATUSES = {
    TenderProcessStatus.EXTRACTED,
    TenderProcessStatus.FAILED,
    TenderProcessStatus.EXPORTED,
}


class PermanentFileProcessingError(RuntimeError):
    pass


class InternalExtractionWorker:
    def __init__(
        self,
        *,
        metadata_store: MetadataStore,
        blob_service: BlobStorageService,
        submission_store: EntityStoreSubmissionService,
        queue_service: ExtractionQueueService,
        vision_extractor: VisionExtractor,
        telemetry: ExtractionTelemetry,
        render_dpi: int,
        max_dequeue_count: int = 3,
        visibility_timeout_seconds: int = 600,
        poll_interval_seconds: int = 10,
    ):
        self.metadata_store = metadata_store
        self.blob_service = blob_service
        self.submission_store = submission_store
        self.queue_service = queue_service
        self.vision_extractor = vision_extractor
        self.telemetry = telemetry
        self.render_dpi = render_dpi
        self.max_dequeue_count = max_dequeue_count
        self.visibility_timeout_seconds = visibility_timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds

    def _audit_blob_prefix(self, batch_id: str, tender_file_id: str) -> str:
        return f"_{{internal}}/extraction-results/{batch_id}/{tender_file_id}"

    def _tender_file_transaction_id(
        self,
        payload: ExtractionBatchMessage,
        tender_file_id: str,
    ) -> str:
        return f"{payload.reference}:{tender_file_id}"

    def _update_batch_running(self, payload: ExtractionBatchMessage) -> None:
        self.metadata_store.update_batch(
            payload.tender_id,
            payload.batch_id,
            {
                'status': 'running',
                'last_error': '',
                'completed_at': '',
                'submission_owner': '',
                'submission_locked_until': '',
            },
        )

    def _finalize_batch(self, payload: ExtractionBatchMessage) -> str:
        progress = self.submission_store.get_batch_progress(payload.reference)
        status_counts = progress.get('status_counts', {})
        total_files = int(progress.get('total_files', 0))

        if total_files == 0:
            final_status = 'failed'
        elif int(status_counts.get('queued', 0)) > 0:
            final_status = 'running'
        elif int(status_counts.get('extracted', 0)) > 0:
            final_status = 'completed'
        else:
            final_status = 'failed'

        self.metadata_store.update_batch(
            payload.tender_id,
            payload.batch_id,
            {
                'status': final_status,
                'completed_at': datetime.now(UTC).replace(tzinfo=None).isoformat()
                if final_status in {'completed', 'failed'}
                else '',
                'submission_owner': '',
                'submission_locked_until': '',
                'last_error': ''
                if final_status != 'failed'
                else (
                    (self.metadata_store.get_batch(payload.tender_id, payload.batch_id) or {})
                    .get('last_error', '')
                ),
            },
        )
        self.telemetry.record_batch_completion(
            tender_id=payload.tender_id,
            batch_id=payload.batch_id,
            status=final_status,
        )
        return final_status

    def _mark_remaining_files_failed(
        self,
        payload: ExtractionBatchMessage,
        batch: Dict,
        error_message: str,
    ) -> None:
        context = self.submission_store.ensure_submission_records(
            tender_id=payload.tender_id,
            file_paths=batch.get('file_paths', []),
            submitted_by=batch.get('submitted_by', 'system'),
            reference=payload.reference,
            sharepoint_folder_path=batch.get('sharepoint_folder_path', ''),
            output_folder_path=batch.get('output_folder_path', ''),
            folder_list=batch.get('folder_list', []),
        )

        for file_path in batch.get('file_paths', []):
            tender_file = context.files_by_path.get(file_path)
            if tender_file is None or tender_file.status in TERMINAL_FILE_STATUSES:
                continue
            self.submission_store.mark_tender_file_failed(
                tender_file,
                transaction_id=self._tender_file_transaction_id(
                    payload,
                    str(tender_file.id),
                ),
                last_error=error_message,
            )

        self.metadata_store.update_batch(
            payload.tender_id,
            payload.batch_id,
            {
                'last_error': error_message,
                'submission_owner': '',
                'submission_locked_until': '',
            },
        )
        self._finalize_batch(payload)

    def _process_single_file(
        self,
        *,
        payload: ExtractionBatchMessage,
        batch: Dict,
        file_path: str,
        tender_file,
    ) -> None:
        file_info = self.blob_service.download_file(payload.tender_id, file_path)
        filename = file_info['filename']
        content_type = (file_info.get('content_type') or '').lower()
        if not filename.lower().endswith('.pdf') and 'pdf' not in content_type:
            raise PermanentFileProcessingError("Only PDF drawings are supported")

        rendered = render_title_block_region(
            file_info['content'],
            batch.get('title_block_coords', {}),
            render_dpi=self.render_dpi,
        )

        extraction_result = self.vision_extractor.extract_title_block(
            crop_png=rendered.crop_png,
            context_png=rendered.context_png,
            filename=filename,
        )
        self.telemetry.record_token_usage(
            tender_id=payload.tender_id,
            batch_id=payload.batch_id,
            total_tokens=extraction_result.total_tokens,
        )

        tender_file_id = str(tender_file.id)
        audit_prefix = self._audit_blob_prefix(payload.batch_id, tender_file_id)
        self.blob_service.upload_bytes(
            f"{audit_prefix}/title-block.png",
            rendered.crop_png,
            content_type='image/png',
        )
        self.blob_service.upload_bytes(
            f"{audit_prefix}/model-response.json",
            extraction_result.raw_response_json.encode('utf-8'),
            content_type='application/json',
        )

        if not extraction_has_values(extraction_result.extraction):
            raise PermanentFileProcessingError(
                "Structured extraction returned no title block metadata"
            )

        self.submission_store.mark_tender_file_extracted(
            tender_file,
            drawing_number=extraction_result.extraction.drawing_number,
            drawing_revision=extraction_result.extraction.drawing_revision,
            revision_date=extraction_result.extraction.revision_date,
            drawing_title=extraction_result.extraction.drawing_title,
            transaction_id=self._tender_file_transaction_id(payload, tender_file_id),
        )

    def process_batch(self, payload: ExtractionBatchMessage) -> str:
        batch = self.metadata_store.get_batch(payload.tender_id, payload.batch_id)
        if not batch:
            logger.warning(
                "Extraction batch not found during worker processing tender_id=%s batch_id=%s",
                payload.tender_id,
                payload.batch_id,
            )
            return 'missing'

        self._update_batch_running(payload)
        context = self.submission_store.ensure_submission_records(
            tender_id=payload.tender_id,
            file_paths=batch.get('file_paths', []),
            submitted_by=batch.get('submitted_by', 'system'),
            reference=payload.reference,
            sharepoint_folder_path=batch.get('sharepoint_folder_path', ''),
            output_folder_path=batch.get('output_folder_path', ''),
            folder_list=batch.get('folder_list', []),
        )

        for file_path in batch.get('file_paths', []):
            tender_file = context.files_by_path.get(file_path)
            if tender_file is None:
                raise RuntimeError(f"No TenderFile record exists for {file_path}")
            if tender_file.status in TERMINAL_FILE_STATUSES:
                continue

            started_at = time.perf_counter()
            try:
                self._process_single_file(
                    payload=payload,
                    batch=batch,
                    file_path=file_path,
                    tender_file=tender_file,
                )
            except PermanentFileProcessingError as exc:
                self.submission_store.mark_tender_file_failed(
                    tender_file,
                    transaction_id=self._tender_file_transaction_id(
                        payload,
                        str(tender_file.id),
                    ),
                    last_error=str(exc),
                )
                self.metadata_store.update_batch(
                    payload.tender_id,
                    payload.batch_id,
                    {'last_error': str(exc)},
                )
                self.telemetry.record_model_failure(
                    tender_id=payload.tender_id,
                    batch_id=payload.batch_id,
                    reason=str(exc),
                )
            except VisionExtractorError as exc:
                self.submission_store.mark_tender_file_failed(
                    tender_file,
                    transaction_id=self._tender_file_transaction_id(
                        payload,
                        str(tender_file.id),
                    ),
                    last_error=str(exc),
                )
                self.metadata_store.update_batch(
                    payload.tender_id,
                    payload.batch_id,
                    {'last_error': str(exc)},
                )
                self.telemetry.record_model_failure(
                    tender_id=payload.tender_id,
                    batch_id=payload.batch_id,
                    reason=str(exc),
                )
            finally:
                latency_ms = (time.perf_counter() - started_at) * 1000
                self.telemetry.record_file_latency(
                    tender_id=payload.tender_id,
                    batch_id=payload.batch_id,
                    file_path=file_path,
                    latency_ms=latency_ms,
                )

        return self._finalize_batch(payload)

    def handle_queue_message(self, queue_message) -> None:
        try:
            payload = ExtractionBatchMessage.from_json(queue_message.content)
        except Exception as exc:
            logger.error("Discarding invalid queue message: %s", exc, exc_info=True)
            self.queue_service.delete_message(queue_message)
            return

        dequeue_count = int(getattr(queue_message, 'dequeue_count', 1) or 1)
        self.telemetry.record_dequeue(
            tender_id=payload.tender_id,
            batch_id=payload.batch_id,
            dequeue_count=dequeue_count,
        )

        try:
            self.process_batch(payload)
        except RetryableVisionError as exc:
            logger.warning(
                "Retryable vision error for batch %s/%s (attempt %s/%s): %s",
                payload.tender_id,
                payload.batch_id,
                dequeue_count,
                self.max_dequeue_count,
                exc,
            )
            self.metadata_store.update_batch(
                payload.tender_id,
                payload.batch_id,
                {'last_error': str(exc)},
            )
            if dequeue_count >= self.max_dequeue_count:
                batch = self.metadata_store.get_batch(payload.tender_id, payload.batch_id) or {}
                self._mark_remaining_files_failed(payload, batch, str(exc))
                self.queue_service.delete_message(queue_message)
            return
        except Exception as exc:
            logger.error(
                "Worker failed for batch %s/%s (attempt %s/%s): %s",
                payload.tender_id,
                payload.batch_id,
                dequeue_count,
                self.max_dequeue_count,
                exc,
                exc_info=True,
            )
            self.metadata_store.update_batch(
                payload.tender_id,
                payload.batch_id,
                {'last_error': str(exc)},
            )
            if dequeue_count >= self.max_dequeue_count:
                batch = self.metadata_store.get_batch(payload.tender_id, payload.batch_id) or {}
                self._mark_remaining_files_failed(payload, batch, str(exc))
                self.queue_service.delete_message(queue_message)
            return

        self.queue_service.delete_message(queue_message)

    def run_forever(self, *, concurrency: int) -> None:
        logger.info(
            "Starting internal extraction worker loop concurrency=%s visibility_timeout=%s poll_interval=%s",
            concurrency,
            self.visibility_timeout_seconds,
            self.poll_interval_seconds,
        )

        with ThreadPoolExecutor(max_workers=max(1, concurrency)) as executor:
            in_flight: Dict[Future, object] = {}

            while True:
                completed = [future for future in in_flight if future.done()]
                for future in completed:
                    try:
                        future.result()
                    except Exception:
                        logger.exception("Unhandled queue worker future failure")
                    in_flight.pop(future, None)

                capacity = max(0, concurrency - len(in_flight))
                if capacity > 0:
                    messages = self.queue_service.receive_messages(
                        max_messages=capacity,
                        visibility_timeout=self.visibility_timeout_seconds,
                    )
                    if messages:
                        for message in messages:
                            in_flight[executor.submit(self.handle_queue_message, message)] = message
                        continue

                if in_flight:
                    done, _ = wait(
                        list(in_flight.keys()),
                        timeout=self.poll_interval_seconds,
                        return_when=FIRST_COMPLETED,
                    )
                    if done:
                        continue
                else:
                    time.sleep(self.poll_interval_seconds)


def build_worker_from_environment(
    *,
    metadata_store: MetadataStore,
    blob_service: BlobStorageService,
    submission_store: EntityStoreSubmissionService,
    queue_service: ExtractionQueueService,
    vision_extractor: VisionExtractor,
    telemetry: ExtractionTelemetry,
) -> InternalExtractionWorker:
    return InternalExtractionWorker(
        metadata_store=metadata_store,
        blob_service=blob_service,
        submission_store=submission_store,
        queue_service=queue_service,
        vision_extractor=vision_extractor,
        telemetry=telemetry,
        render_dpi=int(os.getenv('EXTRACTION_RENDER_DPI', '300')),
        max_dequeue_count=int(os.getenv('EXTRACTION_QUEUE_MAX_DEQUEUE_COUNT', '3')),
        visibility_timeout_seconds=int(
            os.getenv('EXTRACTION_QUEUE_VISIBILITY_TIMEOUT_SECONDS', '600')
        ),
        poll_interval_seconds=int(os.getenv('EXTRACTION_WORKER_POLL_INTERVAL_SECONDS', '10')),
    )
