"""
Blob metadata store adapter.
"""
import logging
from typing import Dict, List, Optional

from services.blob_storage import BlobStorageService
from services.metadata_store import MetadataStore

logger = logging.getLogger(__name__)


class BlobMetadataStore(MetadataStore):
    """Metadata store implementation backed by blob metadata."""

    def __init__(self, blob_service: BlobStorageService):
        self.blob_service = blob_service

    def list_tenders(self) -> List[Dict]:
        return self.blob_service.list_tenders()

    def create_tender(self, tender_name: str, created_by: str, metadata: Dict = None) -> Dict:
        return self.blob_service.create_tender(tender_name, created_by, metadata)

    def get_tender(self, tender_id: str) -> Optional[Dict]:
        return self.blob_service.get_tender(tender_id)

    def delete_tender(self, tender_id: str) -> bool:
        # Blob mode deletes tender content directly via blob_service.delete_tender in app flow.
        return True

    def upsert_tender_record(self, tender: Dict) -> Dict:
        return tender

    def list_files(self, tender_id: str, exclude_batched: bool = False) -> List[Dict]:
        return self.blob_service.list_files(tender_id, exclude_batched=exclude_batched)

    def get_file(self, tender_id: str, file_path: str) -> Optional[Dict]:
        return self.blob_service.get_file_info(tender_id, file_path)

    def upsert_file_record(self, tender_id: str, file_record: Dict) -> Dict:
        # Blob upload paths already set metadata; keep this as a compatibility pass-through.
        file_path = file_record.get('path')
        if file_path:
            metadata_updates = {}
            for field in ['category', 'uploaded_by', 'uploaded_at', 'source', 'batch_id', 'submitted_at']:
                if field in file_record and file_record.get(field) is not None:
                    metadata_updates[field] = file_record.get(field)
            if metadata_updates:
                try:
                    self.blob_service.update_file_metadata(
                        tender_id=tender_id,
                        file_path=file_path,
                        metadata=metadata_updates
                    )
                except Exception as exc:
                    logger.warning("Blob metadata upsert failed for %s: %s", file_path, exc)
        return file_record

    def restore_file_record(self, tender_id: str, file_record: Dict) -> Dict:
        return self.upsert_file_record(tender_id, file_record)

    def update_file_metadata(self, tender_id: str, file_path: str, metadata: Dict) -> Optional[Dict]:
        self.blob_service.update_file_metadata(tender_id=tender_id, file_path=file_path, metadata=metadata)
        return self.get_file(tender_id, file_path)

    def delete_file_metadata(self, tender_id: str, file_path: str) -> bool:
        # Blob metadata is attached to content; app flow deletes blob next.
        return True

    def create_batch(self, tender_id: str, batch_name: str, discipline: str,
                     file_paths: List[str], title_block_coords: Dict,
                     submitted_by: str, job_id: Optional[str] = None,
                     sharepoint_folder_path: Optional[str] = None,
                     output_folder_path: Optional[str] = None,
                     folder_list: Optional[List[str]] = None) -> Dict:
        return self.blob_service.create_batch(
            tender_id=tender_id,
            batch_name=batch_name,
            discipline=discipline,
            file_paths=file_paths,
            title_block_coords=title_block_coords,
            submitted_by=submitted_by,
            job_id=job_id,
            sharepoint_folder_path=sharepoint_folder_path,
            output_folder_path=output_folder_path,
            folder_list=folder_list
        )

    def upsert_batch_record(self, tender_id: str, batch_record: Dict) -> Dict:
        return self.blob_service.upsert_batch_record(tender_id, batch_record)

    def list_batches(self, tender_id: str) -> List[Dict]:
        return self.blob_service.list_batches(tender_id)

    def get_batch(self, tender_id: str, batch_id: str) -> Optional[Dict]:
        return self.blob_service.get_batch(tender_id, batch_id)

    def get_batch_by_reference(self, reference: str) -> Optional[Dict]:
        return self.blob_service.get_batch_by_reference(reference)

    def update_batch_status(self, tender_id: str, batch_id: str, status: str) -> Optional[Dict]:
        return self.blob_service.update_batch_status(tender_id, batch_id, status)

    def update_batch(self, tender_id: str, batch_id: str, updates: Dict) -> Optional[Dict]:
        return self.blob_service.update_batch(tender_id, batch_id, updates)

    def get_batch_files(self, tender_id: str, batch_id: str) -> List[Dict]:
        return self.blob_service.get_batch_files(tender_id, batch_id)

    def update_files_category(self, tender_id: str, file_paths: List[str],
                              category: str, batch_id: str) -> int:
        return self.blob_service.update_files_category(tender_id, file_paths, category, batch_id)

    def delete_batch(self, tender_id: str, batch_id: str) -> bool:
        return self.blob_service.delete_batch(tender_id, batch_id)

    def check_health(self) -> Dict:
        try:
            if not self.blob_service.container_client:
                return {'ok': False, 'store': 'blob', 'error': 'Blob container client is not configured'}
            self.blob_service.container_client.get_container_properties()
            return {'ok': True, 'store': 'blob'}
        except Exception as exc:
            return {'ok': False, 'store': 'blob', 'error': str(exc)}
