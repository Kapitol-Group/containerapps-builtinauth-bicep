"""
Cosmos DB metadata store implementation.
"""
import hashlib
import logging
import random
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from azure.cosmos import CosmosClient, PartitionKey, exceptions
from azure.core import MatchConditions
from azure.identity import DefaultAzureCredential

from services.metadata_store import MetadataStore

logger = logging.getLogger(__name__)

VALID_BATCH_STATUSES = {'pending', 'submitting', 'running', 'completed', 'failed'}
FILE_COUNT_RETRY_LIMIT = 3
FILE_COUNT_RETRY_BASE_SECONDS = 0.05


class CosmosMetadataStore(MetadataStore):
    """Metadata store implementation backed by Azure Cosmos DB."""

    def __init__(
        self,
        account_endpoint: str,
        database_name: str = 'kapitol-tender-automation',
        metadata_container_name: str = 'metadata',
        batch_reference_container_name: str = 'batch-reference-index',
    ):
        if not account_endpoint:
            raise ValueError("COSMOS_ACCOUNT_ENDPOINT is required for Cosmos metadata store")

        self.account_endpoint = account_endpoint
        self.database_name = database_name
        self.metadata_container_name = metadata_container_name
        self.batch_reference_container_name = batch_reference_container_name

        self.client = CosmosClient(
            url=account_endpoint,
            credential=DefaultAzureCredential(),
        )
        self.database = self.client.create_database_if_not_exists(id=database_name)
        self.metadata_container = self.database.create_container_if_not_exists(
            id=metadata_container_name,
            partition_key=PartitionKey(path='/tender_id'),
        )
        self.reference_container = self.database.create_container_if_not_exists(
            id=batch_reference_container_name,
            partition_key=PartitionKey(path='/reference'),
        )

    @staticmethod
    def _utc_now() -> str:
        return datetime.utcnow().isoformat()

    @staticmethod
    def _tender_doc_id(tender_id: str) -> str:
        return f"tender::{tender_id}"

    @staticmethod
    def _file_doc_id(file_path: str) -> str:
        digest = hashlib.sha256(file_path.encode('utf-8')).hexdigest()
        return f"file::{digest}"

    @staticmethod
    def _batch_doc_id(batch_id: str) -> str:
        return f"batch::{batch_id}"

    @staticmethod
    def _reference_doc_id(reference: str) -> str:
        return f"ref::{reference}"

    def _read_item(self, container, doc_id: str, partition_key: str) -> Optional[Dict]:
        try:
            return container.read_item(item=doc_id, partition_key=partition_key)
        except exceptions.CosmosResourceNotFoundError:
            return None

    def _query_metadata(self, query: str, parameters: List[Dict]) -> List[Dict]:
        return list(
            self.metadata_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True,
            )
        )

    def _query_reference(self, query: str, parameters: List[Dict]) -> List[Dict]:
        return list(
            self.reference_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True,
            )
        )

    def _upsert_reference_index(self, reference: str, tender_id: str, batch_id: str):
        if not reference:
            return
        doc = {
            'id': self._reference_doc_id(reference),
            'doc_type': 'batch_reference',
            'reference': reference,
            'tender_id': tender_id,
            'batch_id': batch_id,
            'updated_at': self._utc_now(),
        }
        self.reference_container.upsert_item(doc)

    def _delete_reference_index(self, reference: str):
        if not reference:
            return
        try:
            self.reference_container.delete_item(
                item=self._reference_doc_id(reference),
                partition_key=reference
            )
        except exceptions.CosmosResourceNotFoundError:
            return

    def _to_tender(self, doc: Dict) -> Dict:
        return {
            'id': doc.get('tender_id'),
            'name': doc.get('name', doc.get('tender_id')),
            'created_at': doc.get('created_at'),
            'created_by': doc.get('created_by'),
            'file_count': int(doc.get('file_count', 0)),
            'sharepoint_path': doc.get('sharepoint_path'),
            'output_location': doc.get('output_location'),
            'sharepoint_site_id': doc.get('sharepoint_site_id'),
            'sharepoint_library_id': doc.get('sharepoint_library_id'),
            'sharepoint_folder_path': doc.get('sharepoint_folder_path'),
            'output_site_id': doc.get('output_site_id'),
            'output_library_id': doc.get('output_library_id'),
            'output_folder_path': doc.get('output_folder_path'),
        }

    @staticmethod
    def _to_file(doc: Dict) -> Dict:
        return {
            'name': doc.get('name') or (doc.get('path', '').split('/')[-1] if doc.get('path') else None),
            'path': doc.get('path'),
            'size': int(doc.get('size', 0)),
            'content_type': doc.get('content_type'),
            'category': doc.get('category', 'uncategorized'),
            'uploaded_by': doc.get('uploaded_by'),
            'uploaded_at': doc.get('uploaded_at'),
            'last_modified': doc.get('last_modified'),
            'source': doc.get('source', 'local'),
            'batch_id': doc.get('batch_id') or None,
            'submitted_at': doc.get('submitted_at'),
        }

    def _batch_file_paths(self, tender_id: str, batch_id: str) -> List[str]:
        items = self._query_metadata(
            "SELECT c.path FROM c WHERE c.tender_id=@tender_id AND c.doc_type='file' AND c.batch_id=@batch_id",
            [
                {'name': '@tender_id', 'value': tender_id},
                {'name': '@batch_id', 'value': batch_id},
            ]
        )
        return [item.get('path') for item in items if item.get('path')]

    def _batch_paths_for_tender(self, tender_id: str) -> Dict[str, List[str]]:
        items = self._query_metadata(
            "SELECT c.batch_id, c.path FROM c WHERE c.tender_id=@tender_id AND c.doc_type='file' AND IS_DEFINED(c.batch_id) AND c.batch_id != ''",
            [{'name': '@tender_id', 'value': tender_id}],
        )
        mapping: Dict[str, List[str]] = {}
        for item in items:
            batch_id = item.get('batch_id')
            path = item.get('path')
            if not batch_id or not path:
                continue
            mapping.setdefault(batch_id, []).append(path)
        return mapping

    def _to_batch(self, doc: Dict, file_paths: Optional[List[str]] = None) -> Dict:
        batch_id = doc.get('batch_id')
        return {
            'batch_id': batch_id,
            'batch_name': doc.get('batch_name'),
            'discipline': doc.get('discipline'),
            'file_paths': file_paths if file_paths is not None else self._batch_file_paths(doc.get('tender_id'), batch_id),
            'title_block_coords': doc.get('title_block_coords', {}),
            'status': doc.get('status', 'pending'),
            'submitted_at': doc.get('submitted_at'),
            'submitted_by': doc.get('submitted_by'),
            'file_count': int(doc.get('file_count', 0)),
            'job_id': doc.get('job_id', ''),
            'submission_attempts': doc.get('submission_attempts', []),
            'last_error': doc.get('last_error', ''),
            'uipath_reference': doc.get('uipath_reference', ''),
            'uipath_submission_id': doc.get('uipath_submission_id', ''),
            'uipath_project_id': doc.get('uipath_project_id', ''),
            'submission_owner': doc.get('submission_owner', ''),
            'submission_locked_until': doc.get('submission_locked_until', ''),
            'sharepoint_folder_path': doc.get('sharepoint_folder_path', ''),
            'output_folder_path': doc.get('output_folder_path', ''),
            'folder_list': doc.get('folder_list', []),
        }

    @staticmethod
    def _status_code(exc: Exception) -> Optional[int]:
        status_code = getattr(exc, 'status_code', None)
        try:
            return int(status_code) if status_code is not None else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _is_conflict_status(status_code: Optional[int]) -> bool:
        return status_code in {409, 412}

    @staticmethod
    def _is_atomic_batch_unsupported(exc: Exception) -> bool:
        status_code = CosmosMetadataStore._status_code(exc)
        if status_code != 400:
            return False
        message = str(exc).lower()
        return 'patch' in message and 'batch' in message

    @staticmethod
    def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _sleep_before_retry(attempt: int):
        base = FILE_COUNT_RETRY_BASE_SECONDS * max(1, attempt)
        time.sleep(base + random.uniform(0.0, FILE_COUNT_RETRY_BASE_SECONDS))

    def _patch_tender_count_operation(self, delta: int) -> List[Dict[str, Any]]:
        return [
            {'op': 'incr', 'path': '/file_count', 'value': delta},
            {'op': 'set', 'path': '/updated_at', 'value': self._utc_now()},
        ]

    def _apply_tender_count_delta_with_optimistic_retry(
        self,
        tender_id: str,
        delta: int,
        file_path: str,
        operation: str,
    ) -> bool:
        for attempt in range(1, FILE_COUNT_RETRY_LIMIT + 1):
            tender_doc = self._read_item(
                self.metadata_container,
                self._tender_doc_id(tender_id),
                tender_id
            )
            if not tender_doc:
                return False
            current_count = int(tender_doc.get('file_count', 0))
            tender_doc['file_count'] = max(0, current_count + delta)
            tender_doc['updated_at'] = self._utc_now()

            try:
                self.metadata_container.replace_item(
                    item=tender_doc['id'],
                    body=tender_doc,
                    etag=tender_doc.get('_etag'),
                    match_condition=MatchConditions.IfNotModified
                )
                return True
            except Exception as exc:
                status_code = self._status_code(exc)
                if self._is_conflict_status(status_code):
                    logger.info(
                        "file_count_atomic_update_retry tender_id=%s file_path=%s operation=%s attempt=%s status_code=%s",
                        tender_id,
                        file_path,
                        operation,
                        attempt,
                        status_code,
                    )
                    if attempt < FILE_COUNT_RETRY_LIMIT:
                        self._sleep_before_retry(attempt)
                        continue
                    logger.warning(
                        "file_count_atomic_update_conflict tender_id=%s file_path=%s operation=%s attempts=%s outcome=failed",
                        tender_id,
                        file_path,
                        operation,
                        FILE_COUNT_RETRY_LIMIT,
                    )
                raise
        return False

    def _create_file_and_increment_count_optimistic(self, tender_id: str, file_doc: Dict[str, Any]):
        file_path = file_doc.get('path', '')
        try:
            self.metadata_container.create_item(file_doc)
        except Exception as exc:
            status_code = self._status_code(exc)
            if status_code == 409:
                self.metadata_container.upsert_item(file_doc)
                return
            raise

        try:
            if not self._apply_tender_count_delta_with_optimistic_retry(
                tender_id=tender_id,
                delta=1,
                file_path=file_path,
                operation='create',
            ):
                raise RuntimeError("Tender record not found while updating file_count")
        except Exception:
            try:
                self.metadata_container.delete_item(item=file_doc['id'], partition_key=tender_id)
            except Exception:
                logger.error(
                    "Rollback failed after optimistic file_count increment failure for tender_id=%s file_path=%s",
                    tender_id,
                    file_path,
                    exc_info=True,
                )
            raise

    def _delete_file_and_decrement_count_optimistic(self, tender_id: str, file_doc: Dict[str, Any]):
        file_path = file_doc.get('path', '')
        file_doc_id = file_doc['id']
        file_etag = file_doc.get('_etag')
        try:
            self.metadata_container.delete_item(
                item=file_doc_id,
                partition_key=tender_id,
                etag=file_etag,
                match_condition=MatchConditions.IfNotModified,
            )
        except exceptions.CosmosResourceNotFoundError:
            return False

        try:
            if not self._apply_tender_count_delta_with_optimistic_retry(
                tender_id=tender_id,
                delta=-1,
                file_path=file_path,
                operation='delete',
            ):
                raise RuntimeError("Tender record not found while updating file_count")
        except Exception:
            restore_doc = dict(file_doc)
            restore_doc.pop('_etag', None)
            try:
                self.metadata_container.upsert_item(restore_doc)
            except Exception:
                logger.error(
                    "Rollback failed after optimistic file_count decrement failure for tender_id=%s file_path=%s",
                    tender_id,
                    file_path,
                    exc_info=True,
                )
            raise
        return True

    def _create_file_and_increment_count(self, tender_id: str, file_doc: Dict[str, Any]):
        batch_operations = [
            ('create', (file_doc,)),
            ('patch', (
                self._tender_doc_id(tender_id),
                self._patch_tender_count_operation(delta=1),
            )),
        ]
        self.metadata_container.execute_item_batch(
            batch_operations=batch_operations,
            partition_key=tender_id,
        )

    def _delete_file_and_decrement_count(self, tender_id: str, file_doc_id: str, file_etag: Optional[str]):
        batch_operations = [
            ('delete', (file_doc_id,), {'if_match_etag': file_etag}),
            ('patch', (
                self._tender_doc_id(tender_id),
                self._patch_tender_count_operation(delta=-1),
            )),
        ]
        self.metadata_container.execute_item_batch(
            batch_operations=batch_operations,
            partition_key=tender_id,
        )

    def recompute_tender_file_count(self, tender_id: str) -> int:
        rows = self._query_metadata(
            "SELECT VALUE COUNT(1) FROM c WHERE c.tender_id=@tender_id AND c.doc_type='file'",
            [{'name': '@tender_id', 'value': tender_id}],
        )
        count = int(rows[0]) if rows else 0
        tender_doc = self._read_item(
            self.metadata_container,
            self._tender_doc_id(tender_id),
            tender_id
        )
        if tender_doc:
            previous_count = int(tender_doc.get('file_count', 0))
            tender_doc['file_count'] = count
            tender_doc['updated_at'] = self._utc_now()
            self.metadata_container.upsert_item(tender_doc)
            if previous_count != count:
                logger.info(
                    "file_count_reconciliation_fix tender_id=%s previous_count=%s recomputed_count=%s",
                    tender_id,
                    previous_count,
                    count,
                )
        return count

    def list_tenders(self) -> List[Dict]:
        docs = self._query_metadata(
            "SELECT * FROM c WHERE c.doc_type='tender'",
            []
        )
        return [self._to_tender(doc) for doc in docs]

    def create_tender(self, tender_name: str, created_by: str, metadata: Dict = None) -> Dict:
        tender_id = tender_name.replace(' ', '-').lower()
        metadata = metadata or {}
        doc = {
            'id': self._tender_doc_id(tender_id),
            'doc_type': 'tender',
            'tender_id': tender_id,
            'name': tender_name,
            'created_by': created_by,
            'created_at': metadata.get('created_at') or self._utc_now(),
            'file_count': int(metadata.get('file_count', 0)),
            'updated_at': self._utc_now(),
        }
        for field in [
            'sharepoint_path', 'output_location',
            'sharepoint_site_id', 'sharepoint_library_id', 'sharepoint_folder_path',
            'output_site_id', 'output_library_id', 'output_folder_path'
        ]:
            if field in metadata:
                doc[field] = metadata.get(field)

        self.metadata_container.upsert_item(doc)
        return self._to_tender(doc)

    def get_tender(self, tender_id: str) -> Optional[Dict]:
        doc = self._read_item(self.metadata_container, self._tender_doc_id(tender_id), tender_id)
        if not doc:
            return None
        return self._to_tender(doc)

    def delete_tender(self, tender_id: str) -> bool:
        docs = self._query_metadata(
            "SELECT c.id FROM c WHERE c.tender_id=@tender_id",
            [{'name': '@tender_id', 'value': tender_id}],
        )
        for doc in docs:
            try:
                self.metadata_container.delete_item(item=doc['id'], partition_key=tender_id)
            except exceptions.CosmosResourceNotFoundError:
                continue

        refs = self._query_reference(
            "SELECT c.id, c.reference FROM c WHERE c.tender_id=@tender_id",
            [{'name': '@tender_id', 'value': tender_id}],
        )
        for ref in refs:
            try:
                self.reference_container.delete_item(
                    item=ref['id'],
                    partition_key=ref['reference']
                )
            except exceptions.CosmosResourceNotFoundError:
                continue
        return True

    def upsert_tender_record(self, tender: Dict) -> Dict:
        tender_id = tender.get('id') or tender.get('tender_id')
        if not tender_id:
            raise ValueError("Tender record requires id or tender_id")

        doc = {
            'id': self._tender_doc_id(tender_id),
            'doc_type': 'tender',
            'tender_id': tender_id,
            'name': tender.get('name', tender_id),
            'created_at': tender.get('created_at'),
            'created_by': tender.get('created_by'),
            'file_count': int(tender.get('file_count', 0)),
            'updated_at': self._utc_now(),
        }
        for field in [
            'sharepoint_path', 'output_location',
            'sharepoint_site_id', 'sharepoint_library_id', 'sharepoint_folder_path',
            'output_site_id', 'output_library_id', 'output_folder_path'
        ]:
            if field in tender:
                doc[field] = tender.get(field)

        self.metadata_container.upsert_item(doc)
        return self._to_tender(doc)

    def list_files(self, tender_id: str, exclude_batched: bool = False) -> List[Dict]:
        query = "SELECT * FROM c WHERE c.tender_id=@tender_id AND c.doc_type='file'"
        if exclude_batched:
            query += " AND (NOT IS_DEFINED(c.batch_id) OR c.batch_id = '')"
        docs = self._query_metadata(query, [{'name': '@tender_id', 'value': tender_id}])
        files = [self._to_file(doc) for doc in docs]
        files.sort(key=lambda item: item.get('last_modified') or item.get('uploaded_at') or '', reverse=True)
        return files

    def get_file(self, tender_id: str, file_path: str) -> Optional[Dict]:
        doc = self._read_item(
            self.metadata_container,
            self._file_doc_id(file_path),
            tender_id
        )
        if not doc:
            return None
        return self._to_file(doc)

    def upsert_file_record(self, tender_id: str, file_record: Dict) -> Dict:
        file_path = file_record.get('path')
        if not file_path:
            raise ValueError("File record requires path")

        doc_id = self._file_doc_id(file_path)
        doc = {
            'id': doc_id,
            'doc_type': 'file',
            'tender_id': tender_id,
            'path': file_path,
            'name': file_record.get('name') or file_path.split('/')[-1],
            'size': int(file_record.get('size', 0)),
            'content_type': file_record.get('content_type'),
            'category': file_record.get('category', 'uncategorized'),
            'uploaded_by': file_record.get('uploaded_by'),
            'uploaded_at': file_record.get('uploaded_at'),
            'last_modified': file_record.get('last_modified') or self._utc_now(),
            'source': file_record.get('source', 'local'),
            'batch_id': file_record.get('batch_id') or '',
            'submitted_at': file_record.get('submitted_at'),
            'updated_at': self._utc_now(),
        }
        for attempt in range(1, FILE_COUNT_RETRY_LIMIT + 1):
            existing = self._read_item(self.metadata_container, doc_id, tender_id)
            if existing:
                self.metadata_container.upsert_item(doc)
                return self._to_file(doc)

            try:
                self._create_file_and_increment_count(tender_id, doc)
                return self._to_file(doc)
            except Exception as exc:
                status_code = self._status_code(exc)
                if self._is_atomic_batch_unsupported(exc):
                    logger.warning(
                        "Transactional batch patch unsupported for tender_id=%s file_path=%s. Falling back to optimistic concurrency.",
                        tender_id,
                        file_path,
                    )
                    self._create_file_and_increment_count_optimistic(tender_id, doc)
                    return self._to_file(doc)

                if self._is_conflict_status(status_code):
                    logger.info(
                        "file_count_atomic_update_retry tender_id=%s file_path=%s operation=create attempt=%s status_code=%s",
                        tender_id,
                        file_path,
                        attempt,
                        status_code,
                    )
                    if attempt < FILE_COUNT_RETRY_LIMIT:
                        self._sleep_before_retry(attempt)
                        continue
                    logger.warning(
                        "file_count_atomic_update_conflict tender_id=%s file_path=%s operation=create attempts=%s outcome=failed",
                        tender_id,
                        file_path,
                        FILE_COUNT_RETRY_LIMIT,
                    )
                raise

        raise RuntimeError(f"Failed to upsert file metadata for {file_path}")

    def restore_file_record(self, tender_id: str, file_record: Dict) -> Dict:
        return self.upsert_file_record(tender_id, file_record)

    def update_file_metadata(self, tender_id: str, file_path: str, metadata: Dict) -> Optional[Dict]:
        doc_id = self._file_doc_id(file_path)
        doc = self._read_item(self.metadata_container, doc_id, tender_id)
        if not doc:
            return None
        for key, value in metadata.items():
            if key in {'batch_id'}:
                doc[key] = value or ''
            else:
                doc[key] = value
        doc['updated_at'] = self._utc_now()
        self.metadata_container.upsert_item(doc)
        return self._to_file(doc)

    def delete_file_metadata(self, tender_id: str, file_path: str) -> bool:
        doc_id = self._file_doc_id(file_path)
        for attempt in range(1, FILE_COUNT_RETRY_LIMIT + 1):
            existing = self._read_item(self.metadata_container, doc_id, tender_id)
            if not existing:
                return False

            try:
                self._delete_file_and_decrement_count(
                    tender_id=tender_id,
                    file_doc_id=doc_id,
                    file_etag=existing.get('_etag'),
                )
                return True
            except Exception as exc:
                status_code = self._status_code(exc)
                if self._is_atomic_batch_unsupported(exc):
                    logger.warning(
                        "Transactional batch patch unsupported for tender_id=%s file_path=%s. Falling back to optimistic concurrency.",
                        tender_id,
                        file_path,
                    )
                    return self._delete_file_and_decrement_count_optimistic(tender_id, existing)

                if self._is_conflict_status(status_code):
                    logger.info(
                        "file_count_atomic_update_retry tender_id=%s file_path=%s operation=delete attempt=%s status_code=%s",
                        tender_id,
                        file_path,
                        attempt,
                        status_code,
                    )
                    if attempt < FILE_COUNT_RETRY_LIMIT:
                        self._sleep_before_retry(attempt)
                        continue

                    latest = self._read_item(self.metadata_container, doc_id, tender_id)
                    if not latest:
                        return False
                    logger.warning(
                        "file_count_atomic_update_conflict tender_id=%s file_path=%s operation=delete attempts=%s outcome=failed",
                        tender_id,
                        file_path,
                        FILE_COUNT_RETRY_LIMIT,
                    )
                raise

        return False

    def create_batch(self, tender_id: str, batch_name: str, discipline: str,
                     file_paths: List[str], title_block_coords: Dict,
                     submitted_by: str, job_id: Optional[str] = None,
                     sharepoint_folder_path: Optional[str] = None,
                     output_folder_path: Optional[str] = None,
                     folder_list: Optional[List[str]] = None) -> Dict:
        batch_id = str(uuid.uuid4())
        submitted_at = self._utc_now()
        doc = {
            'id': self._batch_doc_id(batch_id),
            'doc_type': 'batch',
            'tender_id': tender_id,
            'batch_id': batch_id,
            'batch_name': batch_name,
            'discipline': discipline,
            'status': 'pending',
            'submitted_at': submitted_at,
            'submitted_by': submitted_by,
            'file_count': len(file_paths),
            'job_id': job_id or '',
            'submission_attempts': [],
            'last_error': '',
            'uipath_reference': '',
            'uipath_submission_id': '',
            'uipath_project_id': '',
            'submission_owner': '',
            'submission_locked_until': '',
            'sharepoint_folder_path': sharepoint_folder_path or '',
            'output_folder_path': output_folder_path or '',
            'folder_list': folder_list or [],
            'title_block_coords': title_block_coords or {},
            'updated_at': self._utc_now(),
        }
        self.metadata_container.upsert_item(doc)
        return self._to_batch(doc, file_paths=file_paths)

    def upsert_batch_record(self, tender_id: str, batch_record: Dict) -> Dict:
        batch_id = batch_record.get('batch_id') or str(uuid.uuid4())
        existing_doc = self._read_item(self.metadata_container, self._batch_doc_id(batch_id), tender_id) or {}
        existing_reference = existing_doc.get('uipath_reference', '')

        doc = {
            'id': self._batch_doc_id(batch_id),
            'doc_type': 'batch',
            'tender_id': tender_id,
            'batch_id': batch_id,
            'batch_name': batch_record.get('batch_name', existing_doc.get('batch_name', batch_id)),
            'discipline': batch_record.get('discipline', existing_doc.get('discipline')),
            'status': batch_record.get('status', existing_doc.get('status', 'pending')),
            'submitted_at': batch_record.get('submitted_at', existing_doc.get('submitted_at', self._utc_now())),
            'submitted_by': batch_record.get('submitted_by', existing_doc.get('submitted_by')),
            'file_count': int(batch_record.get('file_count', existing_doc.get('file_count', 0))),
            'job_id': batch_record.get('job_id', existing_doc.get('job_id', '')),
            'submission_attempts': batch_record.get('submission_attempts', existing_doc.get('submission_attempts', [])),
            'last_error': batch_record.get('last_error', existing_doc.get('last_error', '')),
            'uipath_reference': batch_record.get('uipath_reference', existing_doc.get('uipath_reference', '')),
            'uipath_submission_id': batch_record.get('uipath_submission_id', existing_doc.get('uipath_submission_id', '')),
            'uipath_project_id': batch_record.get('uipath_project_id', existing_doc.get('uipath_project_id', '')),
            'submission_owner': batch_record.get('submission_owner', existing_doc.get('submission_owner', '')),
            'submission_locked_until': batch_record.get('submission_locked_until', existing_doc.get('submission_locked_until', '')),
            'sharepoint_folder_path': batch_record.get('sharepoint_folder_path', existing_doc.get('sharepoint_folder_path', '')),
            'output_folder_path': batch_record.get('output_folder_path', existing_doc.get('output_folder_path', '')),
            'folder_list': batch_record.get('folder_list', existing_doc.get('folder_list', [])),
            'title_block_coords': batch_record.get('title_block_coords', existing_doc.get('title_block_coords', {})),
            'updated_at': self._utc_now(),
        }
        self.metadata_container.upsert_item(doc)

        new_reference = doc.get('uipath_reference', '')
        if existing_reference and existing_reference != new_reference:
            self._delete_reference_index(existing_reference)
        if new_reference:
            self._upsert_reference_index(new_reference, tender_id, batch_id)

        file_paths = batch_record.get('file_paths')
        return self._to_batch(doc, file_paths=file_paths)

    def list_batches(self, tender_id: str) -> List[Dict]:
        docs = self._query_metadata(
            "SELECT * FROM c WHERE c.tender_id=@tender_id AND c.doc_type='batch'",
            [{'name': '@tender_id', 'value': tender_id}],
        )
        paths_by_batch = self._batch_paths_for_tender(tender_id)
        batches = [self._to_batch(doc, file_paths=paths_by_batch.get(doc.get('batch_id'), [])) for doc in docs]
        batches.sort(key=lambda item: item.get('submitted_at') or '', reverse=True)
        return batches

    def get_batch(self, tender_id: str, batch_id: str) -> Optional[Dict]:
        doc = self._read_item(self.metadata_container, self._batch_doc_id(batch_id), tender_id)
        if not doc:
            return None
        return self._to_batch(doc)

    def get_batch_by_reference(self, reference: str) -> Optional[Dict]:
        if not reference:
            return None

        ref_doc = self._read_item(
            self.reference_container,
            self._reference_doc_id(reference),
            reference
        )
        if not ref_doc:
            refs = self._query_reference(
                "SELECT * FROM c WHERE c.reference=@reference",
                [{'name': '@reference', 'value': reference}],
            )
            ref_doc = refs[0] if refs else None
            if not ref_doc:
                return None

        tender_id = ref_doc.get('tender_id')
        batch_id = ref_doc.get('batch_id')
        if not tender_id or not batch_id:
            return None
        batch = self.get_batch(tender_id, batch_id)
        if not batch:
            return None
        return {
            'tender_id': tender_id,
            'batch': batch,
        }

    def update_batch_status(self, tender_id: str, batch_id: str, status: str) -> Optional[Dict]:
        if status not in VALID_BATCH_STATUSES:
            raise ValueError(f"Invalid status. Must be one of: {', '.join(sorted(VALID_BATCH_STATUSES))}")
        return self.update_batch(tender_id, batch_id, {'status': status})

    def update_batch(self, tender_id: str, batch_id: str, updates: Dict) -> Optional[Dict]:
        doc = self._read_item(self.metadata_container, self._batch_doc_id(batch_id), tender_id)
        if not doc:
            return None

        previous_reference = doc.get('uipath_reference', '')
        for key, value in updates.items():
            if key in {'submission_attempts'} and value is None:
                doc[key] = []
            elif key in {'folder_list'} and value is None:
                doc[key] = []
            elif key in {'title_block_coords'} and value is None:
                doc[key] = {}
            elif key in {'file_count'} and value is not None:
                doc[key] = int(value)
            elif value is None:
                doc[key] = ''
            else:
                doc[key] = value

        if doc.get('status') not in VALID_BATCH_STATUSES:
            doc['status'] = 'pending'

        doc['updated_at'] = self._utc_now()
        self.metadata_container.upsert_item(doc)

        new_reference = doc.get('uipath_reference', '')
        if previous_reference and previous_reference != new_reference:
            self._delete_reference_index(previous_reference)
        if new_reference:
            self._upsert_reference_index(new_reference, tender_id, batch_id)

        return self._to_batch(doc)

    def claim_batch_for_submission(self, tender_id: str, batch_id: str,
                                   owner: str, allowed_statuses: List[str],
                                   lock_seconds: int,
                                   attempt_source: Optional[str] = None,
                                   submitted_by: Optional[str] = None) -> Optional[Dict]:
        allowed = set(allowed_statuses or [])
        if not allowed:
            return None

        max_attempts = 5
        for attempt in range(1, max_attempts + 1):
            doc = self._read_item(self.metadata_container, self._batch_doc_id(batch_id), tender_id)
            if not doc:
                return None

            now = datetime.utcnow()
            status = doc.get('status', 'pending')
            existing_owner = doc.get('submission_owner', '')
            lock_until = self._parse_iso_datetime(doc.get('submission_locked_until', ''))
            lock_active = bool(status == 'submitting' and lock_until and lock_until > now)

            if status == 'submitting' and lock_active and existing_owner != owner:
                return None

            can_claim = status in allowed or (status == 'submitting' and (not lock_active or existing_owner == owner))
            if not can_claim:
                return None

            submission_attempts = doc.get('submission_attempts')
            if not isinstance(submission_attempts, list):
                submission_attempts = []
            submission_attempts.append({
                'timestamp': now.isoformat(),
                'status': 'in_progress',
                'source': attempt_source or 'unknown'
            })

            doc['status'] = 'submitting'
            doc['submission_owner'] = owner
            doc['submission_locked_until'] = (now + timedelta(seconds=max(30, int(lock_seconds)))).isoformat()
            doc['submission_attempts'] = submission_attempts
            doc['updated_at'] = now.isoformat()
            doc['last_error'] = ''
            if submitted_by:
                doc['submitted_by'] = submitted_by

            try:
                self.metadata_container.replace_item(
                    item=doc['id'],
                    body=doc,
                    etag=doc.get('_etag'),
                    match_condition=MatchConditions.IfNotModified
                )
                return self.get_batch(tender_id, batch_id)
            except Exception as exc:
                if self._is_conflict_status(self._status_code(exc)) and attempt < max_attempts:
                    self._sleep_before_retry(attempt)
                    continue
                if self._is_conflict_status(self._status_code(exc)):
                    return None
                raise

        return None

    def get_batch_files(self, tender_id: str, batch_id: str) -> List[Dict]:
        docs = self._query_metadata(
            "SELECT * FROM c WHERE c.tender_id=@tender_id AND c.doc_type='file' AND c.batch_id=@batch_id",
            [
                {'name': '@tender_id', 'value': tender_id},
                {'name': '@batch_id', 'value': batch_id},
            ],
        )
        files = [self._to_file(doc) for doc in docs]
        files.sort(key=lambda item: item.get('last_modified') or item.get('uploaded_at') or '', reverse=True)
        return files

    def update_files_category(self, tender_id: str, file_paths: List[str],
                              category: str, batch_id: str) -> int:
        updated_count = 0
        submitted_at = self._utc_now()
        for file_path in file_paths:
            doc_id = self._file_doc_id(file_path)
            doc = self._read_item(self.metadata_container, doc_id, tender_id)
            if not doc:
                continue
            doc['category'] = category
            doc['batch_id'] = batch_id or ''
            doc['submitted_at'] = submitted_at
            doc['updated_at'] = submitted_at
            self.metadata_container.upsert_item(doc)
            updated_count += 1
        return updated_count

    def delete_batch(self, tender_id: str, batch_id: str) -> bool:
        batch_doc = self._read_item(self.metadata_container, self._batch_doc_id(batch_id), tender_id)
        if not batch_doc:
            return False

        files = self.get_batch_files(tender_id, batch_id)
        for file_item in files:
            file_path = file_item.get('path')
            if not file_path:
                continue
            doc = self._read_item(self.metadata_container, self._file_doc_id(file_path), tender_id)
            if not doc:
                continue
            doc['batch_id'] = ''
            doc['submitted_at'] = None
            doc['category'] = 'uncategorized'
            doc['updated_at'] = self._utc_now()
            self.metadata_container.upsert_item(doc)

        self.metadata_container.delete_item(item=self._batch_doc_id(batch_id), partition_key=tender_id)
        if batch_doc.get('uipath_reference'):
            self._delete_reference_index(batch_doc.get('uipath_reference'))
        return True

    def check_health(self) -> Dict:
        try:
            # Lightweight read to verify connectivity/auth.
            self.database.read()
            return {'ok': True, 'store': 'cosmos'}
        except Exception as exc:
            return {'ok': False, 'store': 'cosmos', 'error': str(exc)}
