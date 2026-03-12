from __future__ import annotations

import logging
import os

from services.blob_storage import BlobStorageService
from services.entity_store_submission_service import EntityStoreSubmissionService
from services.extraction_queue import ExtractionQueueService
from services.extraction_telemetry import ExtractionTelemetry, configure_process_telemetry
from services.internal_extraction_worker import build_worker_from_environment
from services.metadata_store_factory import build_metadata_store
from services.vision_extractor import VisionExtractor


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )
    logger = logging.getLogger(__name__)

    configure_process_telemetry('kapitol-extraction-worker')

    blob_service = BlobStorageService(
        account_name=os.getenv('AZURE_STORAGE_ACCOUNT_NAME'),
        container_name=os.getenv('AZURE_STORAGE_CONTAINER_NAME', 'tender-documents'),
    )
    metadata_store = build_metadata_store(blob_service)
    submission_store = EntityStoreSubmissionService(
        metadata_store=metadata_store,
    )
    queue_service = ExtractionQueueService(
        account_name=os.getenv('AZURE_STORAGE_ACCOUNT_NAME', ''),
        queue_name=os.getenv('EXTRACTION_QUEUE_NAME', 'drawing-extraction'),
    )
    vision_extractor = VisionExtractor(
        endpoint=os.getenv('AZURE_OPENAI_ENDPOINT', ''),
        deployment_name=os.getenv('AZURE_OPENAI_EXTRACTION_DEPLOYMENT', ''),
    )
    telemetry = ExtractionTelemetry('kapitol-extraction-worker')

    if not submission_store.is_configured:
        raise RuntimeError("Metadata-backed extraction state store is not configured")
    if not queue_service.is_configured:
        raise RuntimeError("Extraction queue is not configured")
    if not vision_extractor.is_configured:
        raise RuntimeError("Vision extractor is not configured")

    worker = build_worker_from_environment(
        metadata_store=metadata_store,
        blob_service=blob_service,
        submission_store=submission_store,
        queue_service=queue_service,
        vision_extractor=vision_extractor,
        telemetry=telemetry,
    )

    concurrency = int(os.getenv('EXTRACTION_WORKER_CONCURRENCY', '2'))
    logger.info("Starting extraction worker with concurrency=%s", concurrency)
    worker.run_forever(concurrency=concurrency)


if __name__ == '__main__':
    main()
