#!/usr/bin/env python3
"""
Backfill tender/file/batch metadata from Blob metadata into Cosmos DB.
"""
import argparse
import json
import os
import sys
from typing import Dict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from services.blob_metadata_store import BlobMetadataStore
from services.blob_storage import BlobStorageService
from services.cosmos_metadata_store import CosmosMetadataStore


def parse_args():
    parser = argparse.ArgumentParser(description="Backfill metadata from Blob to Cosmos")
    parser.add_argument('--dry-run', action='store_true', help='Report what would be backfilled without writing')
    parser.add_argument('--tender-id', help='Backfill only one tender id')
    return parser.parse_args()


def build_blob_store() -> BlobMetadataStore:
    account_name = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
    container_name = os.getenv('AZURE_STORAGE_CONTAINER_NAME', 'tender-documents')
    print(json.dumps({
        'step': 'blob_store_init',
        'account_name': account_name,
        'container_name': container_name,
    }))
    blob_service = BlobStorageService(
        account_name=account_name,
        container_name=container_name,
        ensure_container=False,
    )
    return BlobMetadataStore(blob_service)


def build_cosmos_store() -> CosmosMetadataStore:
    return CosmosMetadataStore(
        account_endpoint=os.getenv('COSMOS_ACCOUNT_ENDPOINT', ''),
        database_name=os.getenv('COSMOS_DATABASE_NAME', 'kapitol-tender-automation'),
        metadata_container_name=os.getenv('COSMOS_METADATA_CONTAINER_NAME', 'metadata'),
        batch_reference_container_name=os.getenv('COSMOS_BATCH_REFERENCE_CONTAINER_NAME', 'batch-reference-index'),
    )


def main():
    args = parse_args()

    blob_store = build_blob_store()
    cosmos_store = None if args.dry_run and not os.getenv('COSMOS_ACCOUNT_ENDPOINT') else build_cosmos_store()

    tenders = blob_store.list_tenders()
    if args.tender_id:
        tenders = [t for t in tenders if t.get('id') == args.tender_id]

    summary: Dict[str, int] = {
        'tenders_total': len(tenders),
        'tenders_upserted': 0,
        'files_upserted': 0,
        'batches_upserted': 0,
    }

    for tender in tenders:
        tender_id = tender.get('id')
        if not tender_id:
            continue

        files = blob_store.list_files(tender_id, exclude_batched=False)
        batches = blob_store.list_batches(tender_id)

        if not args.dry_run:
            cosmos_store.upsert_tender_record(tender)
            summary['tenders_upserted'] += 1

            for file_item in files:
                cosmos_store.upsert_file_record(tender_id, file_item)
                summary['files_upserted'] += 1

            for batch in batches:
                batch_id = batch.get('batch_id')
                full_batch = blob_store.get_batch(tender_id, batch_id) if batch_id else batch
                if full_batch:
                    cosmos_store.upsert_batch_record(tender_id, full_batch)
                    summary['batches_upserted'] += 1

            cosmos_store.recompute_tender_file_count(tender_id)
        else:
            summary['tenders_upserted'] += 1
            summary['files_upserted'] += len(files)
            summary['batches_upserted'] += len(batches)

        print(
            json.dumps(
                {
                    'tender_id': tender_id,
                    'files': len(files),
                    'batches': len(batches),
                    'dry_run': args.dry_run,
                }
            )
        )

    print(json.dumps({'summary': summary, 'dry_run': args.dry_run}, indent=2))


if __name__ == '__main__':
    main()
