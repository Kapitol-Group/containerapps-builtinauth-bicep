#!/usr/bin/env python3
"""
Validate Cosmos metadata backfill against Blob metadata.
"""
import argparse
import json
import os
import random
import sys
from typing import Any, Dict, List, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from services.blob_metadata_store import BlobMetadataStore
from services.blob_storage import BlobStorageService
from services.cosmos_metadata_store import CosmosMetadataStore


def parse_args():
    parser = argparse.ArgumentParser(description="Validate Blob-to-Cosmos metadata migration")
    parser.add_argument('--sample-size', type=int, default=25, help='Random sample size for file/batch record checks')
    parser.add_argument('--max-mismatches', type=int, default=0, help='Allowed mismatch count before failure')
    parser.add_argument('--tender-id', help='Validate only one tender id')
    return parser.parse_args()


def norm(value: Any) -> Any:
    if value == '':
        return None
    return value


def mismatch(mismatches: List[Dict], kind: str, tender_id: str, identifier: str, field: str, blob_value: Any, cosmos_value: Any):
    mismatches.append({
        'kind': kind,
        'tender_id': tender_id,
        'id': identifier,
        'field': field,
        'blob': blob_value,
        'cosmos': cosmos_value,
    })


def compare_fields(
    mismatches: List[Dict],
    kind: str,
    tender_id: str,
    identifier: str,
    blob_item: Dict,
    cosmos_item: Dict,
    fields: List[str],
):
    for field in fields:
        blob_val = norm(blob_item.get(field))
        cosmos_val = norm(cosmos_item.get(field))
        if blob_val != cosmos_val:
            mismatch(mismatches, kind, tender_id, identifier, field, blob_val, cosmos_val)


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


def sample_items(items: List[Dict], sample_size: int) -> List[Dict]:
    if len(items) <= sample_size:
        return items
    return random.sample(items, sample_size)


def main():
    args = parse_args()
    blob_store = build_blob_store()
    cosmos_store = build_cosmos_store()

    blob_tenders = blob_store.list_tenders()
    cosmos_tenders = cosmos_store.list_tenders()

    if args.tender_id:
        blob_tenders = [t for t in blob_tenders if t.get('id') == args.tender_id]
        cosmos_tenders = [t for t in cosmos_tenders if t.get('id') == args.tender_id]

    blob_tender_map = {t['id']: t for t in blob_tenders if t.get('id')}
    cosmos_tender_map = {t['id']: t for t in cosmos_tenders if t.get('id')}

    mismatches: List[Dict] = []

    blob_ids = set(blob_tender_map.keys())
    cosmos_ids = set(cosmos_tender_map.keys())
    missing_in_cosmos = sorted(blob_ids - cosmos_ids)
    missing_in_blob = sorted(cosmos_ids - blob_ids)

    for tender_id in missing_in_cosmos:
        mismatch(mismatches, 'tender_set', tender_id, tender_id, 'exists', True, False)
    for tender_id in missing_in_blob:
        mismatch(mismatches, 'tender_set', tender_id, tender_id, 'exists', False, True)

    common_tenders = sorted(blob_ids & cosmos_ids)
    file_samples_checked = 0
    batch_samples_checked = 0

    for tender_id in common_tenders:
        blob_tender = blob_tender_map[tender_id]
        cosmos_tender = cosmos_tender_map[tender_id]
        compare_fields(
            mismatches,
            'tender',
            tender_id,
            tender_id,
            blob_tender,
            cosmos_tender,
            ['name', 'created_at', 'created_by']
        )

        blob_files = blob_store.list_files(tender_id, exclude_batched=False)
        cosmos_files = cosmos_store.list_files(tender_id, exclude_batched=False)
        if len(blob_files) != len(cosmos_files):
            mismatch(
                mismatches, 'file_count', tender_id, tender_id, 'count',
                len(blob_files), len(cosmos_files)
            )

        blob_file_map = {f['path']: f for f in blob_files if f.get('path')}
        cosmos_file_map = {f['path']: f for f in cosmos_files if f.get('path')}
        for sample in sample_items(list(blob_file_map.values()), args.sample_size):
            path = sample.get('path')
            cosmos_file = cosmos_file_map.get(path)
            if not cosmos_file:
                mismatch(mismatches, 'file_missing', tender_id, path, 'exists', True, False)
                continue
            compare_fields(
                mismatches,
                'file',
                tender_id,
                path,
                sample,
                cosmos_file,
                ['category', 'source', 'batch_id']
            )
            file_samples_checked += 1

        blob_batches = blob_store.list_batches(tender_id)
        cosmos_batches = cosmos_store.list_batches(tender_id)
        if len(blob_batches) != len(cosmos_batches):
            mismatch(
                mismatches, 'batch_count', tender_id, tender_id, 'count',
                len(blob_batches), len(cosmos_batches)
            )

        cosmos_batch_map = {b['batch_id']: b for b in cosmos_batches if b.get('batch_id')}
        for sample in sample_items(blob_batches, args.sample_size):
            batch_id = sample.get('batch_id')
            cosmos_batch = cosmos_batch_map.get(batch_id)
            if not cosmos_batch:
                mismatch(mismatches, 'batch_missing', tender_id, batch_id, 'exists', True, False)
                continue
            compare_fields(
                mismatches,
                'batch',
                tender_id,
                batch_id,
                sample,
                cosmos_batch,
                ['batch_name', 'discipline', 'status', 'submitted_by', 'file_count', 'uipath_reference']
            )
            blob_paths = sorted(sample.get('file_paths', []))
            cosmos_paths = sorted(cosmos_batch.get('file_paths', []))
            if blob_paths != cosmos_paths:
                mismatch(mismatches, 'batch', tender_id, batch_id, 'file_paths', blob_paths, cosmos_paths)
            batch_samples_checked += 1

    report = {
        'summary': {
            'blob_tenders': len(blob_tenders),
            'cosmos_tenders': len(cosmos_tenders),
            'common_tenders': len(common_tenders),
            'file_samples_checked': file_samples_checked,
            'batch_samples_checked': batch_samples_checked,
            'mismatch_count': len(mismatches),
            'max_mismatches_allowed': args.max_mismatches,
        },
        'mismatches': mismatches[:500],
    }

    print(json.dumps(report, indent=2))

    if len(mismatches) > args.max_mismatches:
        sys.exit(1)


if __name__ == '__main__':
    main()
