#!/usr/bin/env python3
"""
Reconcile Cosmos tender file_count fields with actual file document counts.
"""
from services.cosmos_metadata_store import CosmosMetadataStore
import argparse
import json
import os
import sys
from typing import Dict, List

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Reconcile Cosmos tender file counts")
    parser.add_argument('--dry-run', action='store_true',
                        help='Report mismatches without writing fixes')
    parser.add_argument('--tender-id', help='Reconcile only one tender id')
    return parser.parse_args()


def build_cosmos_store() -> CosmosMetadataStore:
    return CosmosMetadataStore(
        account_endpoint=os.getenv(
            'COSMOS_ACCOUNT_ENDPOINT', 'https://tenderdevndqk4pnzhzrjacosmos.documents.azure.com:443/'),
        database_name=os.getenv('COSMOS_DATABASE_NAME',
                                'kapitol-tender-automation'),
        metadata_container_name=os.getenv(
            'COSMOS_METADATA_CONTAINER_NAME', 'metadata'),
        batch_reference_container_name=os.getenv(
            'COSMOS_BATCH_REFERENCE_CONTAINER_NAME', 'batch-reference-index'),
    )


def count_files(cosmos_store: CosmosMetadataStore, tender_id: str) -> int:
    rows = cosmos_store._query_metadata(
        "SELECT VALUE COUNT(1) FROM c WHERE c.tender_id=@tender_id AND c.doc_type='file'",
        [{'name': '@tender_id', 'value': tender_id}],
    )
    return int(rows[0]) if rows else 0


def main():
    args = parse_args()
    cosmos_store = build_cosmos_store()

    tenders = cosmos_store.list_tenders()
    if args.tender_id:
        tenders = [t for t in tenders if t.get('id') == args.tender_id]

    mismatches: List[Dict] = []
    fixed_count = 0

    for tender in tenders:
        tender_id = tender.get('id')
        if not tender_id:
            continue

        actual_count = count_files(cosmos_store, tender_id)
        stored_count = int(tender.get('file_count', 0))

        if stored_count != actual_count:
            mismatch = {
                'tender_id': tender_id,
                'stored_count': stored_count,
                'actual_count': actual_count,
                'fixed': False,
            }
            if not args.dry_run:
                cosmos_store.recompute_tender_file_count(tender_id)
                mismatch['fixed'] = True
                fixed_count += 1
            mismatches.append(mismatch)

    report = {
        'summary': {
            'dry_run': args.dry_run,
            'tenders_scanned': len(tenders),
            'mismatched_tenders': len(mismatches),
            'fixed_tenders': fixed_count,
        },
        'mismatches': mismatches,
    }

    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
