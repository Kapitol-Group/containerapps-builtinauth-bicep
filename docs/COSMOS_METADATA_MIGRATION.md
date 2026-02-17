# Cosmos Metadata Migration Runbook

## Overview

This runbook covers rollout of metadata storage from Blob metadata to Cosmos DB while keeping Blob Storage for binary file content.

## Prerequisites

- Infrastructure deployed from `infra/main.bicep` with:
  - Cosmos account in serverless mode
  - SQL database and containers:
    - `metadata` (or configured name)
    - `batch-reference-index` (or configured name)
  - Cosmos SQL data contributor role assignment for the ACA managed identity
- Backend deployed with metadata store abstraction and migration scripts.

## Environment Variables

Required for `dual` and `cosmos` modes:

- `COSMOS_ACCOUNT_ENDPOINT`
- `COSMOS_DATABASE_NAME`
- `COSMOS_METADATA_CONTAINER_NAME`
- `COSMOS_BATCH_REFERENCE_CONTAINER_NAME`

Mode controls:

- `METADATA_STORE_MODE`: `blob`, `dual`, `cosmos`
- `METADATA_READ_FALLBACK`: `true`/`false`

## Backfill

### Automatic (default via `azd provision`)

`infra/hooks/postprovision.sh` runs the migration sequence automatically unless explicitly disabled:

```bash
azd env set AUTO_RUN_COSMOS_BACKFILL "false"
```

Automatic sequence:

1. Dry-run backfill
2. Full backfill
3. Validation (`--sample-size 25 --max-mismatches 0`)

Hook logs are written to:

- `.azure/logs/postprovision-cosmos-migration-latest.log`
- `.azure/logs/postprovision-cosmos-migration-<timestamp>.log`

If provision reports no infra changes, run a forced provision to trigger hooks:

```bash
azd provision --force
```

### Manual

Run from backend directory:

```bash
python scripts/backfill_metadata_to_cosmos.py --dry-run
python scripts/backfill_metadata_to_cosmos.py
```

Single tender:

```bash
python scripts/backfill_metadata_to_cosmos.py --tender-id <tender-id>
```

## Validation

```bash
python scripts/validate_cosmos_backfill.py --sample-size 25 --max-mismatches 0
```

Single tender:

```bash
python scripts/validate_cosmos_backfill.py --tender-id <tender-id>
```

Non-zero exit code indicates mismatch threshold exceeded.

## Rollout Sequence

1. Deploy with:
   - `METADATA_STORE_MODE=blob`
   - `METADATA_READ_FALLBACK=true`
2. Run backfill dry run and validation.
3. Run full backfill and validation.
4. Switch to:
   - `METADATA_STORE_MODE=dual`
   - `METADATA_READ_FALLBACK=true`
5. Observe logs for fallback hits, compensation events, and reference-index misses.
6. Switch to:
   - `METADATA_STORE_MODE=cosmos`
   - `METADATA_READ_FALLBACK=false`
7. After stabilization window, treat Blob metadata as legacy only.

## Operational Checks

- `/api/health` now reports:
  - `metadata_mode`
  - metadata store health status
- Verify webhook updates by submitting a completed/failed callback and ensuring batch status updates via reference index lookup.
- Verify delete compensation behavior:
  - Metadata deletion + blob deletion for files
  - Metadata restore if blob delete fails

## Rollback

If issues occur:

1. Set `METADATA_STORE_MODE=blob`.
2. Keep `METADATA_READ_FALLBACK=true`.
3. Redeploy.

This restores legacy blob metadata read/write behavior while preserving Cosmos data for later replay.
