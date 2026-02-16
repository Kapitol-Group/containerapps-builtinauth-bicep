---
name: preprocess-har-sessions
description: Normalize and filter HTTP Archive (.har) exports into compact JSON session logs for debugging and testing. Use when asked to extract relevant API requests/responses from large HAR files, isolate one or more session_state values, redact sensitive fields, or generate reproducible session slices for analysis.
---

# Preprocess HAR Sessions

## Overview
Convert HAR exports into a stable session-log JSON format and reduce noise before analysis.
Use the bundled script for deterministic extraction, filtering, and redaction.

## Quick Start
1. Run the preprocessor script:
```bash
python3 scripts/preprocess_har.py /path/to/network.har --summary
```
2. Open the output path printed by the script (default: `<input-stem>.sessions.json`).
3. Continue debugging on that normalized JSON file.

## Workflow
1. Start with broad extraction, then add filters.
2. Keep only relevant traffic using URL/method/status/session filters.
3. Keep redaction enabled unless explicitly asked for raw secrets.
4. Trim very large payloads with `--max-body-chars` when sharing logs.

## Script
Use `scripts/preprocess_har.py`.

Common options:
- `--url-contains <text>`: Keep entries where URL contains text (repeat for OR).
- `--url-regex <pattern>`: Keep entries matching regex.
- `--host <host>`: Keep entries by host (repeat for OR).
- `--method <METHOD>`: Keep entries by method.
- `--status <code>`: Keep entries by HTTP status.
- `--session-state <id>`: Keep entries with extracted `session_state`.
- `--from-time <iso>` / `--to-time <iso>`: Filter by started timestamp.
- `--max-body-chars <n>`: Truncate large payload fields.
- `--decode-base64`: Decode base64 HAR body payloads.
- `--no-redact`: Disable default redaction.
- `--summary`: Print compact extraction stats.

## Output Schema
The script emits an array of objects with:
- `started`
- `method`
- `url`
- `status`
- `request_mime`
- `request_encoding`
- `request_body`
- `response_mime`
- `response_encoding`
- `response_body`
- `source_index`
- `session_state` (when discoverable)

## References
For task recipes and filter combinations, read `references/recipes.md`.
