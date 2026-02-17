"""
Dual metadata store (Cosmos primary, Blob secondary/fallback).
"""
import logging
from typing import Dict, List, Optional

from services.metadata_store import MetadataStore

logger = logging.getLogger(__name__)


class DualMetadataStore(MetadataStore):
    """Read-primary Cosmos store with optional Blob fallback and dual-write behavior."""

    def __init__(self, cosmos_store: MetadataStore, blob_store: MetadataStore, read_fallback: bool = True):
        self.cosmos_store = cosmos_store
        self.blob_store = blob_store
        self.read_fallback = read_fallback
        self.fallback_hits = 0

    def _fallback(self, method_name: str, *args, **kwargs):
        self.fallback_hits += 1
        logger.info("metadata_read_source=blob-fallback method=%s fallback_hits=%s", method_name, self.fallback_hits)
        method = getattr(self.blob_store, method_name)
        return method(*args, **kwargs)

    def _log_primary(self, method_name: str):
        logger.info("metadata_read_source=cosmos method=%s", method_name)

    def list_tenders(self) -> List[Dict]:
        try:
            self._log_primary('list_tenders')
            return self.cosmos_store.list_tenders()
        except Exception:
            if self.read_fallback:
                return self._fallback('list_tenders')
            raise

    def create_tender(self, tender_name: str, created_by: str, metadata: Dict = None) -> Dict:
        created = self.cosmos_store.create_tender(tender_name, created_by, metadata)
        try:
            self.blob_store.create_tender(tender_name, created_by, metadata)
        except Exception as exc:
            logger.error("Dual-write tender create failed for blob: %s", exc)
            try:
                self.cosmos_store.delete_tender(created['id'])
            except Exception as rollback_exc:
                logger.error("Rollback failed for tender create: %s", rollback_exc)
            raise
        return created

    def get_tender(self, tender_id: str) -> Optional[Dict]:
        try:
            self._log_primary('get_tender')
            tender = self.cosmos_store.get_tender(tender_id)
            if tender is None and self.read_fallback:
                return self._fallback('get_tender', tender_id)
            return tender
        except Exception:
            if self.read_fallback:
                return self._fallback('get_tender', tender_id)
            raise

    def delete_tender(self, tender_id: str) -> bool:
        cosmos_result = self.cosmos_store.delete_tender(tender_id)
        self.blob_store.delete_tender(tender_id)
        return cosmos_result

    def upsert_tender_record(self, tender: Dict) -> Dict:
        result = self.cosmos_store.upsert_tender_record(tender)
        self.blob_store.upsert_tender_record(tender)
        return result

    def list_files(self, tender_id: str, exclude_batched: bool = False) -> List[Dict]:
        try:
            self._log_primary('list_files')
            return self.cosmos_store.list_files(tender_id, exclude_batched=exclude_batched)
        except Exception:
            if self.read_fallback:
                return self._fallback('list_files', tender_id, exclude_batched=exclude_batched)
            raise

    def get_file(self, tender_id: str, file_path: str) -> Optional[Dict]:
        try:
            self._log_primary('get_file')
            file_item = self.cosmos_store.get_file(tender_id, file_path)
            if file_item is None and self.read_fallback:
                return self._fallback('get_file', tender_id, file_path)
            return file_item
        except Exception:
            if self.read_fallback:
                return self._fallback('get_file', tender_id, file_path)
            raise

    def upsert_file_record(self, tender_id: str, file_record: Dict) -> Dict:
        result = self.cosmos_store.upsert_file_record(tender_id, file_record)
        self.blob_store.upsert_file_record(tender_id, file_record)
        return result

    def restore_file_record(self, tender_id: str, file_record: Dict) -> Dict:
        result = self.cosmos_store.restore_file_record(tender_id, file_record)
        self.blob_store.restore_file_record(tender_id, file_record)
        return result

    def update_file_metadata(self, tender_id: str, file_path: str, metadata: Dict) -> Optional[Dict]:
        result = self.cosmos_store.update_file_metadata(tender_id, file_path, metadata)
        self.blob_store.update_file_metadata(tender_id, file_path, metadata)
        return result

    def delete_file_metadata(self, tender_id: str, file_path: str) -> bool:
        result = self.cosmos_store.delete_file_metadata(tender_id, file_path)
        self.blob_store.delete_file_metadata(tender_id, file_path)
        return result

    def create_batch(self, tender_id: str, batch_name: str, discipline: str,
                     file_paths: List[str], title_block_coords: Dict,
                     submitted_by: str, job_id: Optional[str] = None,
                     sharepoint_folder_path: Optional[str] = None,
                     output_folder_path: Optional[str] = None,
                     folder_list: Optional[List[str]] = None) -> Dict:
        created = self.cosmos_store.create_batch(
            tender_id=tender_id,
            batch_name=batch_name,
            discipline=discipline,
            file_paths=file_paths,
            title_block_coords=title_block_coords,
            submitted_by=submitted_by,
            job_id=job_id,
            sharepoint_folder_path=sharepoint_folder_path,
            output_folder_path=output_folder_path,
            folder_list=folder_list,
        )
        self.blob_store.upsert_batch_record(tender_id, created)
        return created

    def upsert_batch_record(self, tender_id: str, batch_record: Dict) -> Dict:
        result = self.cosmos_store.upsert_batch_record(tender_id, batch_record)
        self.blob_store.upsert_batch_record(tender_id, batch_record)
        return result

    def list_batches(self, tender_id: str) -> List[Dict]:
        try:
            self._log_primary('list_batches')
            return self.cosmos_store.list_batches(tender_id)
        except Exception:
            if self.read_fallback:
                return self._fallback('list_batches', tender_id)
            raise

    def get_batch(self, tender_id: str, batch_id: str) -> Optional[Dict]:
        try:
            self._log_primary('get_batch')
            batch = self.cosmos_store.get_batch(tender_id, batch_id)
            if batch is None and self.read_fallback:
                return self._fallback('get_batch', tender_id, batch_id)
            return batch
        except Exception:
            if self.read_fallback:
                return self._fallback('get_batch', tender_id, batch_id)
            raise

    def get_batch_by_reference(self, reference: str) -> Optional[Dict]:
        try:
            self._log_primary('get_batch_by_reference')
            result = self.cosmos_store.get_batch_by_reference(reference)
            if result is None and self.read_fallback:
                return self._fallback('get_batch_by_reference', reference)
            return result
        except Exception:
            if self.read_fallback:
                return self._fallback('get_batch_by_reference', reference)
            raise

    def update_batch_status(self, tender_id: str, batch_id: str, status: str) -> Optional[Dict]:
        result = self.cosmos_store.update_batch_status(tender_id, batch_id, status)
        self.blob_store.update_batch_status(tender_id, batch_id, status)
        return result

    def update_batch(self, tender_id: str, batch_id: str, updates: Dict) -> Optional[Dict]:
        result = self.cosmos_store.update_batch(tender_id, batch_id, updates)
        self.blob_store.update_batch(tender_id, batch_id, updates)
        return result

    def get_batch_files(self, tender_id: str, batch_id: str) -> List[Dict]:
        try:
            self._log_primary('get_batch_files')
            return self.cosmos_store.get_batch_files(tender_id, batch_id)
        except Exception:
            if self.read_fallback:
                return self._fallback('get_batch_files', tender_id, batch_id)
            raise

    def update_files_category(self, tender_id: str, file_paths: List[str],
                              category: str, batch_id: str) -> int:
        count = self.cosmos_store.update_files_category(tender_id, file_paths, category, batch_id)
        self.blob_store.update_files_category(tender_id, file_paths, category, batch_id)
        return count

    def delete_batch(self, tender_id: str, batch_id: str) -> bool:
        deleted = self.cosmos_store.delete_batch(tender_id, batch_id)
        self.blob_store.delete_batch(tender_id, batch_id)
        return deleted

    def check_health(self) -> Dict:
        cosmos_health = self.cosmos_store.check_health()
        blob_health = self.blob_store.check_health()
        return {
            'ok': bool(cosmos_health.get('ok')) and bool(blob_health.get('ok')),
            'store': 'dual',
            'cosmos': cosmos_health,
            'blob': blob_health,
            'fallback_hits': self.fallback_hits,
            'read_fallback': self.read_fallback,
        }
