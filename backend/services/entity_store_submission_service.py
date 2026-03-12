from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from entity_store_transformation_client.models.tender_process_status import (
    TenderProcessStatus,
)

from services.batch_metrics import build_batch_metrics
from services.metadata_store import MetadataStore

logger = logging.getLogger(__name__)


@dataclass
class StoredTenderFile:
    id: str
    tender_id: str
    batch_id: str
    reference: str
    original_path: str
    original_filename: str
    provider: str
    status: TenderProcessStatus
    drawing_number: Optional[str] = None
    drawing_revision: Optional[str] = None
    drawing_title: Optional[str] = None
    destination_path: Optional[str] = None
    transaction_id: Optional[str] = None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
    last_error: Optional[str] = None


@dataclass(frozen=True)
class SubmissionContext:
    reference: str
    submission_id: str
    project_id: str
    files_by_path: Dict[str, StoredTenderFile]


def _status_name(status: TenderProcessStatus | object) -> str:
    if status == TenderProcessStatus.EXPORTED:
        return 'exported'
    if status == TenderProcessStatus.EXTRACTED:
        return 'extracted'
    if status == TenderProcessStatus.FAILED:
        return 'failed'
    return 'queued'


def _status_from_value(value: object) -> TenderProcessStatus:
    if isinstance(value, TenderProcessStatus):
        return value
    if isinstance(value, int):
        try:
            return TenderProcessStatus(value)
        except ValueError:
            return TenderProcessStatus.QUEUED

    normalized = str(value or '').strip().lower()
    mapping = {
        'queued': TenderProcessStatus.QUEUED,
        '1': TenderProcessStatus.QUEUED,
        'extracted': TenderProcessStatus.EXTRACTED,
        '2': TenderProcessStatus.EXTRACTED,
        'failed': TenderProcessStatus.FAILED,
        '3': TenderProcessStatus.FAILED,
        'exported': TenderProcessStatus.EXPORTED,
        '0': TenderProcessStatus.EXPORTED,
    }
    return mapping.get(normalized, TenderProcessStatus.QUEUED)


def _normalize_optional_text(value: object) -> Optional[str]:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _parse_datetime(value: object) -> Optional[datetime]:
    text = _normalize_optional_text(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


class EntityStoreSubmissionService:
    """
    Internal extraction state store backed by the app metadata repository.

    The class name is retained to keep the existing API/worker wiring stable
    while eliminating the UiPath Data Service dependency for extraction state.
    """

    def __init__(self, metadata_store: MetadataStore):
        self.metadata_store = metadata_store

    @property
    def is_configured(self) -> bool:
        return self.metadata_store is not None

    @staticmethod
    def _deterministic_file_id(file_path: str) -> str:
        return hashlib.sha256(file_path.encode('utf-8')).hexdigest()

    def _get_batch_context(self, reference: str) -> Dict:
        batch_context = self.metadata_store.get_batch_by_reference(reference)
        if not batch_context:
            raise RuntimeError(f"Batch with reference '{reference}' was not found")
        return batch_context

    def _to_tender_file(
        self,
        tender_id: str,
        file_record: Dict,
        *,
        reference: str,
    ) -> StoredTenderFile:
        file_path = str(file_record.get('path') or '')
        filename = (
            _normalize_optional_text(file_record.get('name'))
            or file_path.split('/')[-1]
            or 'Unknown'
        )
        extraction_status = _normalize_optional_text(
            file_record.get('extraction_status')
        )
        return StoredTenderFile(
            id=str(file_record.get('id') or self._deterministic_file_id(file_path)),
            tender_id=tender_id,
            batch_id=str(file_record.get('batch_id') or ''),
            reference=reference,
            original_path=file_path,
            original_filename=filename,
            provider=_normalize_optional_text(file_record.get('provider')) or 'internal',
            status=_status_from_value(extraction_status),
            drawing_number=_normalize_optional_text(file_record.get('drawing_number')),
            drawing_revision=_normalize_optional_text(file_record.get('drawing_revision')),
            drawing_title=_normalize_optional_text(file_record.get('drawing_title')),
            destination_path=_normalize_optional_text(file_record.get('destination_path')),
            transaction_id=_normalize_optional_text(file_record.get('transaction_id')),
            create_time=_parse_datetime(
                file_record.get('submitted_at') or file_record.get('uploaded_at')
            ),
            update_time=_parse_datetime(
                file_record.get('extracted_at') or file_record.get('updated_at')
            ),
            last_error=_normalize_optional_text(file_record.get('last_error')),
        )

    def _get_file_record(self, tender_id: str, file_path: str) -> Dict:
        file_record = self.metadata_store.get_file(tender_id, file_path)
        if not file_record:
            raise RuntimeError(
                f"File metadata not found for tender '{tender_id}': {file_path}"
            )
        return file_record

    def ensure_submission_records(
        self,
        tender_id: str,
        file_paths: List[str],
        submitted_by: str,
        reference: str,
        sharepoint_folder_path: Optional[str] = None,
        output_folder_path: Optional[str] = None,
        folder_list: Optional[List[str]] = None,
        provider: str = 'internal',
        reset_failed_files: bool = False,
    ) -> SubmissionContext:
        del submitted_by, sharepoint_folder_path, output_folder_path, folder_list

        if not file_paths:
            raise ValueError("file_paths must contain at least one file")

        files_by_path: Dict[str, StoredTenderFile] = {}
        inferred_batch_id = ''

        for file_path in file_paths:
            file_record = self._get_file_record(tender_id, file_path)
            current_reference = _normalize_optional_text(
                file_record.get('extraction_reference')
            ) or ''
            current_status = _status_from_value(file_record.get('extraction_status'))
            current_batch_id = str(file_record.get('batch_id') or '')
            inferred_batch_id = inferred_batch_id or current_batch_id

            requires_reset = (
                current_reference != reference
                or not _normalize_optional_text(file_record.get('extraction_status'))
                or (reset_failed_files and current_status == TenderProcessStatus.FAILED)
            )
            if requires_reset:
                updated = self.metadata_store.update_file_metadata(
                    tender_id=tender_id,
                    file_path=file_path,
                    metadata={
                        'extraction_status': 'queued',
                        'provider': provider,
                        'drawing_number': '',
                        'drawing_revision': '',
                        'drawing_title': '',
                        'transaction_id': '',
                        'destination_path': '',
                        'extracted_at': '',
                        'last_error': '',
                        'extraction_reference': reference,
                    },
                )
                if updated:
                    file_record = updated
            elif not _normalize_optional_text(file_record.get('provider')):
                updated = self.metadata_store.update_file_metadata(
                    tender_id=tender_id,
                    file_path=file_path,
                    metadata={
                        'provider': provider,
                        'extraction_reference': reference,
                    },
                )
                if updated:
                    file_record = updated

            files_by_path[file_path] = self._to_tender_file(
                tender_id,
                file_record,
                reference=reference,
            )

        submission_id = inferred_batch_id or reference
        return SubmissionContext(
            reference=reference,
            submission_id=submission_id,
            project_id=tender_id,
            files_by_path=files_by_path,
        )

    def get_file_by_reference_and_path(
        self,
        reference: str,
        file_path: str,
    ) -> Optional[StoredTenderFile]:
        batch_context = self._get_batch_context(reference)
        tender_id = batch_context['tender_id']
        batch = batch_context['batch']
        file_record = self.metadata_store.get_file(tender_id, file_path)
        if not file_record:
            return None
        if str(file_record.get('batch_id') or '') != str(batch.get('batch_id') or ''):
            return None
        return self._to_tender_file(tender_id, file_record, reference=reference)

    def update_tender_file(
        self,
        tender_file: StoredTenderFile,
        *,
        status: TenderProcessStatus,
        provider: str,
        drawing_number: Optional[str],
        drawing_revision: Optional[str],
        drawing_title: Optional[str],
        transaction_id: Optional[str],
        last_error: Optional[str] = None,
        destination_path: Optional[str] = None,
    ) -> StoredTenderFile:
        updated = self.metadata_store.update_file_metadata(
            tender_id=tender_file.tender_id,
            file_path=tender_file.original_path,
            metadata={
                'extraction_status': _status_name(status),
                'provider': provider,
                'drawing_number': drawing_number or '',
                'drawing_revision': drawing_revision or '',
                'drawing_title': drawing_title or '',
                'transaction_id': transaction_id or '',
                'destination_path': destination_path or '',
                'extracted_at': datetime.utcnow().isoformat()
                if status in {TenderProcessStatus.EXTRACTED, TenderProcessStatus.FAILED}
                else '',
                'last_error': last_error or '',
                'extraction_reference': tender_file.reference,
            },
        )
        if not updated:
            raise RuntimeError(
                f"Failed to update extraction metadata for {tender_file.original_path}"
            )
        return self._to_tender_file(
            tender_file.tender_id,
            updated,
            reference=tender_file.reference,
        )

    def mark_tender_file_extracted(
        self,
        tender_file: StoredTenderFile,
        *,
        drawing_number: Optional[str],
        drawing_revision: Optional[str],
        drawing_title: Optional[str],
        provider: str = 'internal',
        transaction_id: Optional[str] = None,
    ) -> StoredTenderFile:
        return self.update_tender_file(
            tender_file,
            status=TenderProcessStatus.EXTRACTED,
            provider=provider,
            drawing_number=drawing_number,
            drawing_revision=drawing_revision,
            drawing_title=drawing_title,
            transaction_id=transaction_id,
            last_error=None,
        )

    def mark_tender_file_failed(
        self,
        tender_file: StoredTenderFile,
        *,
        provider: str = 'internal',
        transaction_id: Optional[str] = None,
        last_error: Optional[str] = None,
    ) -> StoredTenderFile:
        return self.update_tender_file(
            tender_file,
            status=TenderProcessStatus.FAILED,
            provider=provider,
            drawing_number=None,
            drawing_revision=None,
            drawing_title=None,
            transaction_id=transaction_id,
            last_error=last_error,
        )

    def reset_tender_file_for_retry(
        self,
        tender_file: StoredTenderFile,
        *,
        provider: str = 'internal',
        transaction_id: Optional[str] = None,
    ) -> StoredTenderFile:
        return self.update_tender_file(
            tender_file,
            status=TenderProcessStatus.QUEUED,
            provider=provider,
            drawing_number=None,
            drawing_revision=None,
            drawing_title=None,
            transaction_id=transaction_id,
            last_error=None,
        )

    def get_batch_progress(self, reference: str) -> Dict:
        batch_context = self._get_batch_context(reference)
        tender_id = batch_context['tender_id']
        batch = batch_context['batch']
        batch_id = str(batch.get('batch_id') or '')

        files = [
            self._to_tender_file(tender_id, file_record, reference=reference)
            for file_record in self.metadata_store.get_batch_files(tender_id, batch_id)
        ]
        status_counts = {
            'queued': 0,
            'extracted': 0,
            'failed': 0,
            'exported': 0,
        }
        file_details = []

        for tender_file in files:
            status_key = _status_name(tender_file.status)
            status_counts[status_key] += 1
            file_details.append(
                {
                    'filename': tender_file.original_filename,
                    'status': status_key,
                    'drawing_number': tender_file.drawing_number,
                    'drawing_revision': tender_file.drawing_revision,
                    'drawing_title': tender_file.drawing_title,
                    'destination_path': tender_file.destination_path,
                    'created_at': tender_file.create_time.isoformat()
                    if tender_file.create_time
                    else None,
                    'updated_at': tender_file.update_time.isoformat()
                    if tender_file.update_time
                    else None,
                }
            )

        progress = {
            'total_files': len(file_details),
            'status_counts': status_counts,
            'files': file_details,
        }
        progress['metrics'] = build_batch_metrics(batch, progress)
        return progress
