"""
Factory for metadata store implementations.
"""
import os

from services.blob_metadata_store import BlobMetadataStore
from services.blob_storage import BlobStorageService
from services.cosmos_metadata_store import CosmosMetadataStore
from services.dual_metadata_store import DualMetadataStore
from services.metadata_store import MetadataStore


def _to_bool(value: str, default: bool = True) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {'1', 'true', 'yes', 'y', 'on'}


def build_metadata_store(blob_service: BlobStorageService) -> MetadataStore:
    mode = os.getenv('METADATA_STORE_MODE', 'blob').strip().lower()
    read_fallback = _to_bool(os.getenv('METADATA_READ_FALLBACK', 'true'), default=True)

    blob_store = BlobMetadataStore(blob_service)

    if mode == 'blob':
        return blob_store

    cosmos_store = CosmosMetadataStore(
        account_endpoint=os.getenv('COSMOS_ACCOUNT_ENDPOINT', ''),
        database_name=os.getenv('COSMOS_DATABASE_NAME', 'kapitol-tender-automation'),
        metadata_container_name=os.getenv('COSMOS_METADATA_CONTAINER_NAME', 'metadata'),
        batch_reference_container_name=os.getenv('COSMOS_BATCH_REFERENCE_CONTAINER_NAME', 'batch-reference-index'),
    )

    if mode == 'cosmos':
        return cosmos_store

    if mode == 'dual':
        return DualMetadataStore(
            cosmos_store=cosmos_store,
            blob_store=blob_store,
            read_fallback=read_fallback,
        )

    raise ValueError(f"Invalid METADATA_STORE_MODE '{mode}'. Expected one of: blob, dual, cosmos")
