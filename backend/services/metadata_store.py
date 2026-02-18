"""
Metadata store abstraction for tender, file, and batch records.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class MetadataStore(ABC):
    """Abstract metadata repository."""

    @abstractmethod
    def list_tenders(self) -> List[Dict]:
        pass

    @abstractmethod
    def create_tender(self, tender_name: str, created_by: str, metadata: Dict = None) -> Dict:
        pass

    @abstractmethod
    def get_tender(self, tender_id: str) -> Optional[Dict]:
        pass

    @abstractmethod
    def delete_tender(self, tender_id: str) -> bool:
        pass

    @abstractmethod
    def upsert_tender_record(self, tender: Dict) -> Dict:
        pass

    @abstractmethod
    def list_files(self, tender_id: str, exclude_batched: bool = False) -> List[Dict]:
        pass

    @abstractmethod
    def get_file(self, tender_id: str, file_path: str) -> Optional[Dict]:
        pass

    @abstractmethod
    def upsert_file_record(self, tender_id: str, file_record: Dict) -> Dict:
        pass

    @abstractmethod
    def restore_file_record(self, tender_id: str, file_record: Dict) -> Dict:
        pass

    @abstractmethod
    def update_file_metadata(self, tender_id: str, file_path: str, metadata: Dict) -> Optional[Dict]:
        pass

    @abstractmethod
    def delete_file_metadata(self, tender_id: str, file_path: str) -> bool:
        pass

    @abstractmethod
    def create_batch(self, tender_id: str, batch_name: str, discipline: str,
                     file_paths: List[str], title_block_coords: Dict,
                     submitted_by: str, job_id: Optional[str] = None,
                     sharepoint_folder_path: Optional[str] = None,
                     output_folder_path: Optional[str] = None,
                     folder_list: Optional[List[str]] = None) -> Dict:
        pass

    @abstractmethod
    def upsert_batch_record(self, tender_id: str, batch_record: Dict) -> Dict:
        pass

    @abstractmethod
    def list_batches(self, tender_id: str) -> List[Dict]:
        pass

    @abstractmethod
    def get_batch(self, tender_id: str, batch_id: str) -> Optional[Dict]:
        pass

    @abstractmethod
    def get_batch_by_reference(self, reference: str) -> Optional[Dict]:
        pass

    @abstractmethod
    def update_batch_status(self, tender_id: str, batch_id: str, status: str) -> Optional[Dict]:
        pass

    @abstractmethod
    def update_batch(self, tender_id: str, batch_id: str, updates: Dict) -> Optional[Dict]:
        pass

    @abstractmethod
    def claim_batch_for_submission(self, tender_id: str, batch_id: str,
                                   owner: str, allowed_statuses: List[str],
                                   lock_seconds: int,
                                   attempt_source: Optional[str] = None,
                                   submitted_by: Optional[str] = None) -> Optional[Dict]:
        pass

    @abstractmethod
    def get_batch_files(self, tender_id: str, batch_id: str) -> List[Dict]:
        pass

    @abstractmethod
    def update_files_category(self, tender_id: str, file_paths: List[str],
                              category: str, batch_id: str) -> int:
        pass

    @abstractmethod
    def delete_batch(self, tender_id: str, batch_id: str) -> bool:
        pass

    @abstractmethod
    def check_health(self) -> Dict:
        pass
