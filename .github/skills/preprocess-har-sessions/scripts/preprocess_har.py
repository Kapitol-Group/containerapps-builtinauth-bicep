#!/usr/bin/env python3
"""Normalize and filter HAR exports into compact session logs."""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

DEFAULT_REDACT_KEYS = {
    'api_key',
    'apikey',
    'authorization',
    'access_token',
    'refresh_token',
    'client_secret',
    'password',
    'secret',
    'token',
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Preprocess a HAR or normalized session JSON file into compact session logs.',
    )
    parser.add_argument('input', help='Input HAR/JSON file path.')
    parser.add_argument(
        '-o',
        '--output',
        help='Output JSON file path. Defaults to <input-stem>.sessions.json in the same directory.',
    )
    parser.add_argument(
        '--url-contains',
        action='append',
        default=[],
        help='Keep entries whose URL contains this substring. Repeat for OR behavior.',
    )
    parser.add_argument('--url-regex', help='Keep entries whose URL matches this regex.')
    parser.add_argument(
        '--host',
        action='append',
        default=[],
        help='Keep entries whose URL host matches this value. Repeat for OR behavior.',
    )
    parser.add_argument(
        '--method',
        action='append',
        default=[],
        help='Keep entries whose HTTP method matches this value. Repeat for OR behavior.',
    )
    parser.add_argument(
        '--status',
        action='append',
        type=int,
        default=[],
        help='Keep entries whose HTTP status matches this value. Repeat for OR behavior.',
    )
    parser.add_argument('--from-time', help='Keep entries with started >= this ISO datetime.')
    parser.add_argument('--to-time', help='Keep entries with started <= this ISO datetime.')
    parser.add_argument(
        '--session-state',
        action='append',
        default=[],
        help='Keep entries matching this session_state value (extracted from request/response bodies).',
    )
    parser.add_argument(
        '--max-body-chars',
        type=int,
        default=0,
        help='Truncate request/response body strings to this length (0 disables truncation).',
    )
    parser.add_argument(
        '--decode-base64',
        action='store_true',
        help='Decode body text when HAR content encoding is base64.',
    )
    parser.add_argument('--limit', type=int, default=0, help='Maximum number of output entries (0 = no limit).')
    parser.add_argument('--no-redact', action='store_true', help='Disable default secret redaction.')
    parser.add_argument(
        '--redact-key',
        action='append',
        default=[],
        help='Additional JSON/query-string key to redact.',
    )
    parser.add_argument('--summary', action='store_true', help='Print processing summary to stderr.')
    return parser.parse_args()


def parse_iso_datetime(raw: str | None) -> datetime | None:
    if not raw:
        return None
    value = raw.strip()
    if value.endswith('Z'):
        value = f'{value[:-1]}+00:00'
    return datetime.fromisoformat(value)


def decode_body(text: Any, encoding: Any, decode_base64: bool) -> Any:
    if not decode_base64:
        return text
    if not isinstance(text, str):
        return text
    if not isinstance(encoding, str) or encoding.lower() != 'base64':
        return text
    try:
        payload = base64.b64decode(text, validate=False)
        return payload.decode('utf-8', errors='replace')
    except Exception:
        return text


def headers_to_dict(headers: Any) -> dict[str, str]:
    values: dict[str, str] = {}
    if not isinstance(headers, list):
        return values
    for header in headers:
        if not isinstance(header, dict):
            continue
        name = header.get('name')
        value = header.get('value')
        if isinstance(name, str) and isinstance(value, str):
            values[name.lower()] = value
    return values


def normalize_har_entry(entry: dict[str, Any], index: int, decode_base64: bool) -> dict[str, Any]:
    request = entry.get('request') if isinstance(entry.get('request'), dict) else {}
    response = entry.get('response') if isinstance(entry.get('response'), dict) else {}

    request_headers = headers_to_dict(request.get('headers'))
    response_headers = headers_to_dict(response.get('headers'))

    post_data = request.get('postData') if isinstance(request.get('postData'), dict) else {}
    content = response.get('content') if isinstance(response.get('content'), dict) else {}

    request_body = decode_body(post_data.get('text'), post_data.get('encoding'), decode_base64)
    response_body = decode_body(content.get('text'), content.get('encoding'), decode_base64)

    return {
        'started': entry.get('startedDateTime'),
        'method': request.get('method'),
        'url': request.get('url'),
        'status': response.get('status'),
        'request_mime': post_data.get('mimeType') or request_headers.get('content-type'),
        'request_encoding': post_data.get('encoding'),
        'request_body': request_body,
        'response_mime': content.get('mimeType') or response_headers.get('content-type'),
        'response_encoding': content.get('encoding'),
        'response_body': response_body,
        'source_index': index,
    }


def normalize_existing_entry(entry: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        'started': entry.get('started'),
        'method': entry.get('method'),
        'url': entry.get('url'),
        'status': entry.get('status'),
        'request_mime': entry.get('request_mime'),
        'request_encoding': entry.get('request_encoding'),
        'request_body': entry.get('request_body'),
        'response_mime': entry.get('response_mime'),
        'response_encoding': entry.get('response_encoding'),
        'response_body': entry.get('response_body'),
        'source_index': entry.get('source_index', index),
        'session_state': entry.get('session_state'),
    }


def extract_entries(payload: Any, decode_base64: bool) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        log = payload.get('log')
        if isinstance(log, dict) and isinstance(log.get('entries'), list):
            return [
                normalize_har_entry(item, index, decode_base64)
                for index, item in enumerate(log['entries'])
                if isinstance(item, dict)
            ]
        if isinstance(payload.get('entries'), list):
            return [
                normalize_har_entry(item, index, decode_base64)
                for index, item in enumerate(payload['entries'])
                if isinstance(item, dict)
            ]

    if isinstance(payload, list):
        sample = next((item for item in payload if isinstance(item, dict)), None)
        if sample and {'started', 'method', 'url'}.issubset(sample.keys()):
            return [
                normalize_existing_entry(item, index)
                for index, item in enumerate(payload)
                if isinstance(item, dict)
            ]
        if sample and ('request' in sample or 'response' in sample):
            return [
                normalize_har_entry(item, index, decode_base64)
                for index, item in enumerate(payload)
                if isinstance(item, dict)
            ]

    raise ValueError('Input JSON is not HAR format and not normalized session-list format.')


def try_json(raw: Any) -> Any:
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text or text[0] not in '{[':
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def recursively_redact_json(value: Any, redact_keys: set[str]) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, nested in value.items():
            key_lower = str(key).lower()
            if key_lower in redact_keys:
                redacted[key] = '[REDACTED]'
            else:
                redacted[key] = recursively_redact_json(nested, redact_keys)
        return redacted
    if isinstance(value, list):
        return [recursively_redact_json(item, redact_keys) for item in value]
    return value


def redact_string(raw: Any, redact_keys: set[str]) -> Any:
    if not isinstance(raw, str):
        return raw

    parsed = try_json(raw)
    if parsed is not None:
        redacted = recursively_redact_json(parsed, redact_keys)
        return json.dumps(redacted, ensure_ascii=False)

    text = raw
    text = re.sub(
        r'(?i)(authorization["\']?\s*:\s*["\']?bearer\s+)[^"\'\s,]+',
        r'\1[REDACTED]',
        text,
    )

    for key in redact_keys:
        key_pattern = re.escape(key)
        text = re.sub(
            rf'(?i)(["\']{key_pattern}["\']\s*:\s*["\'])[^"\']*(["\'])',
            r'\1[REDACTED]\2',
            text,
        )
        text = re.sub(
            rf'(?i)({key_pattern}=)[^&\s"\']+',
            r'\1[REDACTED]',
            text,
        )
    return text


def redact_url(url: Any, redact_keys: set[str]) -> Any:
    if not isinstance(url, str):
        return url
    parts = urlsplit(url)
    if not parts.query:
        return url
    pairs = parse_qsl(parts.query, keep_blank_values=True)
    redacted_pairs = [
        (key, '[REDACTED]' if key.lower() in redact_keys else value)
        for key, value in pairs
    ]
    new_query = urlencode(redacted_pairs, doseq=True)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))


def find_first_session_state(value: Any) -> str | None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if str(key).lower() == 'session_state' and isinstance(nested, str):
                return nested
            found = find_first_session_state(nested)
            if found:
                return found
    if isinstance(value, list):
        for nested in value:
            found = find_first_session_state(nested)
            if found:
                return found
    return None


def extract_session_state(record: dict[str, Any]) -> str | None:
    existing = record.get('session_state')
    if isinstance(existing, str) and existing:
        return existing

    for key in ('request_body', 'response_body'):
        parsed = try_json(record.get(key))
        if parsed is None:
            continue
        found = find_first_session_state(parsed)
        if found:
            return found
    return None


def truncate_text(value: Any, max_chars: int) -> Any:
    if max_chars <= 0 or not isinstance(value, str) or len(value) <= max_chars:
        return value
    return f"{value[:max_chars]}... [truncated {len(value) - max_chars} chars]"


def keep_record(
    record: dict[str, Any],
    url_regex: re.Pattern[str] | None,
    method_filters: set[str],
    status_filters: set[int],
    host_filters: set[str],
    url_contains: list[str],
    from_time: datetime | None,
    to_time: datetime | None,
    session_filters: set[str],
) -> bool:
    url = record.get('url')
    method = str(record.get('method') or '').upper()
    status = record.get('status')
    started = record.get('started')
    session_state = record.get('session_state')

    if method_filters and method not in method_filters:
        return False

    if status_filters and status not in status_filters:
        return False

    if host_filters:
        host = ''
        if isinstance(url, str):
            host = urlsplit(url).netloc.lower()
        if host not in host_filters:
            return False

    if url_contains:
        if not isinstance(url, str) or not any(pattern in url for pattern in url_contains):
            return False

    if url_regex:
        if not isinstance(url, str) or not url_regex.search(url):
            return False

    if session_filters:
        if not isinstance(session_state, str) or session_state not in session_filters:
            return False

    if from_time or to_time:
        try:
            started_dt = parse_iso_datetime(started if isinstance(started, str) else None)
        except ValueError:
            return False
        if started_dt is None:
            return False
        if from_time and started_dt < from_time:
            return False
        if to_time and started_dt > to_time:
            return False

    return True


def default_output_path(input_path: Path) -> Path:
    return input_path.with_name(f'{input_path.stem}.sessions.json')


def build_summary(records: list[dict[str, Any]], input_count: int) -> dict[str, Any]:
    hosts = sorted(
        {
            urlsplit(record['url']).netloc
            for record in records
            if isinstance(record.get('url'), str) and urlsplit(record['url']).netloc
        }
    )
    methods = sorted({str(record.get('method')).upper() for record in records if record.get('method')})
    session_states = sorted(
        {
            record['session_state']
            for record in records
            if isinstance(record.get('session_state'), str) and record['session_state']
        }
    )
    return {
        'input_entries': input_count,
        'output_entries': len(records),
        'methods': methods,
        'hosts': hosts,
        'session_state_count': len(session_states),
    }


def main() -> int:
    args = parse_args()

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        print(f'Input file does not exist: {input_path}', file=sys.stderr)
        return 1

    try:
        raw_payload = json.loads(input_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        print(f'Failed to parse JSON from {input_path}: {exc}', file=sys.stderr)
        return 1

    try:
        records = extract_entries(raw_payload, decode_base64=args.decode_base64)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    redact_keys = {key.lower() for key in DEFAULT_REDACT_KEYS}
    redact_keys.update(key.lower() for key in args.redact_key)

    for record in records:
        if not args.no_redact:
            record['url'] = redact_url(record.get('url'), redact_keys)
            record['request_body'] = redact_string(record.get('request_body'), redact_keys)
            record['response_body'] = redact_string(record.get('response_body'), redact_keys)

        record['session_state'] = extract_session_state(record)
        if args.max_body_chars > 0:
            record['request_body'] = truncate_text(record.get('request_body'), args.max_body_chars)
            record['response_body'] = truncate_text(record.get('response_body'), args.max_body_chars)

    try:
        from_time = parse_iso_datetime(args.from_time)
    except ValueError as exc:
        print(f'Invalid --from-time value: {exc}', file=sys.stderr)
        return 1
    try:
        to_time = parse_iso_datetime(args.to_time)
    except ValueError as exc:
        print(f'Invalid --to-time value: {exc}', file=sys.stderr)
        return 1

    url_regex = None
    if args.url_regex:
        try:
            url_regex = re.compile(args.url_regex)
        except re.error as exc:
            print(f'Invalid --url-regex value: {exc}', file=sys.stderr)
            return 1

    filtered = [
        record
        for record in records
        if keep_record(
            record=record,
            url_regex=url_regex,
            method_filters={item.upper() for item in args.method},
            status_filters=set(args.status),
            host_filters={item.lower() for item in args.host},
            url_contains=args.url_contains,
            from_time=from_time,
            to_time=to_time,
            session_filters=set(args.session_state),
        )
    ]

    if args.limit > 0:
        filtered = filtered[: args.limit]

    output_path = Path(args.output).expanduser().resolve() if args.output else default_output_path(input_path)
    output_path.write_text(json.dumps(filtered, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    if args.summary:
        summary = build_summary(filtered, input_count=len(records))
        print(json.dumps(summary, indent=2), file=sys.stderr)

    print(str(output_path))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
