from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Tuple

METRIC_SOURCE_EXACT = 'exact'
METRIC_SOURCE_ESTIMATED = 'estimated'
METRIC_SOURCE_UNAVAILABLE = 'unavailable'

NON_QUEUED_FILE_STATUSES = {'extracted', 'failed', 'exported'}


def parse_iso_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def normalize_submission_attempts(attempts: Any) -> List[Dict[str, Any]]:
    if not isinstance(attempts, list):
        return []

    normalized: List[Dict[str, Any]] = []
    for raw_attempt in attempts:
        if not isinstance(raw_attempt, dict):
            continue

        started_at = str(
            raw_attempt.get('started_at')
            or raw_attempt.get('timestamp')
            or ''
        ).strip()
        completed_at = str(raw_attempt.get('completed_at') or '').strip()
        status = str(raw_attempt.get('status') or '').strip()
        attempt: Dict[str, Any] = {
            'timestamp': started_at,
            'status': status or 'unknown',
        }

        if started_at:
            attempt['started_at'] = started_at
            attempt['timestamp'] = started_at
        if completed_at:
            attempt['completed_at'] = completed_at

        duration_seconds = _coerce_duration_seconds(
            raw_attempt.get('duration_seconds')
        )
        if duration_seconds is None:
            duration_seconds = _compute_duration_seconds(started_at, completed_at)
        if duration_seconds is not None:
            attempt['duration_seconds'] = duration_seconds

        for field_name in ('reference', 'error', 'source'):
            field_value = str(raw_attempt.get(field_name) or '').strip()
            if field_value:
                attempt[field_name] = field_value

        normalized.append(attempt)

    return normalized


def start_submission_attempt(
    attempts: Any,
    *,
    started_at: datetime,
    source: str,
) -> List[Dict[str, Any]]:
    normalized = normalize_submission_attempts(attempts)
    started_at_text = started_at.isoformat()
    normalized.append(
        {
            'timestamp': started_at_text,
            'started_at': started_at_text,
            'status': 'in_progress',
            'source': str(source or 'unknown').strip() or 'unknown',
        }
    )
    return normalized


def close_active_submission_attempt(
    attempts: Any,
    *,
    completed_at: datetime,
    status: str,
    reference: Optional[str] = None,
    error: Optional[str] = None,
) -> List[Dict[str, Any]]:
    normalized = normalize_submission_attempts(attempts)
    completed_at_text = completed_at.isoformat()

    for attempt in reversed(normalized):
        if attempt.get('status') != 'in_progress':
            continue

        started_at = str(
            attempt.get('started_at')
            or attempt.get('timestamp')
            or ''
        ).strip()
        attempt['status'] = status
        attempt['completed_at'] = completed_at_text
        if started_at:
            attempt['started_at'] = started_at
            attempt['timestamp'] = started_at
        duration_seconds = _compute_duration_seconds(started_at, completed_at_text)
        if duration_seconds is not None:
            attempt['duration_seconds'] = duration_seconds
        if reference:
            attempt['reference'] = str(reference).strip()
        if error:
            attempt['error'] = str(error).strip()
        return normalized

    return normalized


def build_batch_metrics(
    batch: Dict[str, Any],
    progress: Dict[str, Any],
    *,
    now: Optional[datetime] = None,
) -> Dict[str, Dict[str, Any]]:
    current_time = now or datetime.now(UTC).replace(tzinfo=None)
    file_rows = progress.get('files') if isinstance(progress, dict) else []
    if not isinstance(file_rows, list):
        file_rows = []

    progress_timestamps = _collect_progress_timestamps(file_rows)
    submission_metric, submission_end_at = _build_submission_metric(
        batch,
        progress_timestamps,
        current_time,
    )
    completion_metric, completion_at = _build_completion_metric(
        batch,
        progress_timestamps,
    )
    extraction_metric, extraction_end_at = _build_extraction_metric(
        batch,
        progress_timestamps,
        submission_end_at,
        completion_at,
        current_time,
    )
    total_metric = _build_total_metric(
        batch,
        submission_end_at,
        extraction_end_at,
        completion_at,
        submission_metric.get('source'),
        completion_metric.get('source'),
        current_time,
    )
    throughput_metric = _build_throughput_metric(
        progress.get('status_counts') if isinstance(progress, dict) else {},
        extraction_metric,
    )

    return {
        'submission': submission_metric,
        'extraction': extraction_metric,
        'completion': completion_metric,
        'total': total_metric,
        'throughput': throughput_metric,
    }


def _coerce_duration_seconds(value: Any) -> Optional[int]:
    if value is None or value == '':
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed < 0:
        return 0
    return int(round(parsed))


def _compute_duration_seconds(
    started_at: Optional[str],
    completed_at: Optional[str],
) -> Optional[int]:
    started = parse_iso_datetime(started_at)
    ended = parse_iso_datetime(completed_at)
    if not started or not ended:
        return None
    return max(0, int(round((ended - started).total_seconds())))


def _collect_progress_timestamps(file_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    created_at_values: List[datetime] = []
    updated_at_values: List[datetime] = []
    non_queued_updated_at_values: List[datetime] = []
    first_progress_values: List[datetime] = []

    for file_row in file_rows:
        if not isinstance(file_row, dict):
            continue

        created_at = parse_iso_datetime(file_row.get('created_at'))
        updated_at = parse_iso_datetime(file_row.get('updated_at'))
        status = str(file_row.get('status') or '').strip().lower()

        if created_at:
            created_at_values.append(created_at)
            first_progress_values.append(created_at)
        if updated_at:
            updated_at_values.append(updated_at)
            first_progress_values.append(updated_at)
            if status in NON_QUEUED_FILE_STATUSES:
                non_queued_updated_at_values.append(updated_at)

    return {
        'earliest_created_at': min(created_at_values) if created_at_values else None,
        'latest_updated_at': max(updated_at_values) if updated_at_values else None,
        'earliest_non_queued_updated_at': min(non_queued_updated_at_values)
        if non_queued_updated_at_values
        else None,
        'latest_non_queued_updated_at': max(non_queued_updated_at_values)
        if non_queued_updated_at_values
        else None,
        'first_progress_at': min(first_progress_values) if first_progress_values else None,
    }


def _build_submission_metric(
    batch: Dict[str, Any],
    progress_timestamps: Dict[str, Any],
    now: datetime,
) -> Tuple[Dict[str, Any], Optional[datetime]]:
    attempts = normalize_submission_attempts(batch.get('submission_attempts'))
    metric = {
        'duration_seconds': None,
        'attempt_count': len(attempts),
        'source': METRIC_SOURCE_UNAVAILABLE,
    }
    latest_completed_at: Optional[datetime] = None

    if attempts:
        exact_possible = True
        total_duration_seconds = 0

        for attempt in attempts:
            status = str(attempt.get('status') or '').strip().lower()
            started_at = parse_iso_datetime(
                attempt.get('started_at') or attempt.get('timestamp')
            )
            completed_at = parse_iso_datetime(attempt.get('completed_at'))
            duration_seconds = _coerce_duration_seconds(
                attempt.get('duration_seconds')
            )

            if status == 'in_progress':
                if not started_at:
                    exact_possible = False
                    break
                total_duration_seconds += max(
                    0,
                    int(round((now - started_at).total_seconds())),
                )
                continue

            if duration_seconds is not None:
                total_duration_seconds += max(0, duration_seconds)
            elif started_at and completed_at:
                total_duration_seconds += max(
                    0,
                    int(round((completed_at - started_at).total_seconds())),
                )
            else:
                exact_possible = False
                break

            if completed_at and (
                latest_completed_at is None or completed_at > latest_completed_at
            ):
                latest_completed_at = completed_at

        if exact_possible:
            metric['duration_seconds'] = total_duration_seconds
            metric['source'] = METRIC_SOURCE_EXACT
            return metric, latest_completed_at

    submitted_at = parse_iso_datetime(batch.get('submitted_at'))
    first_progress_at = progress_timestamps.get('first_progress_at')
    if submitted_at and first_progress_at and first_progress_at >= submitted_at:
        metric['duration_seconds'] = max(
            0,
            int(round((first_progress_at - submitted_at).total_seconds())),
        )
        metric['source'] = METRIC_SOURCE_ESTIMATED

    return metric, latest_completed_at


def _build_completion_metric(
    batch: Dict[str, Any],
    progress_timestamps: Dict[str, Any],
) -> Tuple[Dict[str, Any], Optional[datetime]]:
    completed_at = parse_iso_datetime(batch.get('completed_at'))
    if completed_at:
        return {
            'completed_at': completed_at.isoformat(),
            'source': METRIC_SOURCE_EXACT,
        }, completed_at

    latest_updated_at = progress_timestamps.get('latest_updated_at')
    if str(batch.get('status') or '').strip().lower() == 'completed' and latest_updated_at:
        return {
            'completed_at': latest_updated_at.isoformat(),
            'source': METRIC_SOURCE_ESTIMATED,
        }, latest_updated_at

    return {
        'completed_at': None,
        'source': METRIC_SOURCE_UNAVAILABLE,
    }, None


def _build_extraction_metric(
    batch: Dict[str, Any],
    progress_timestamps: Dict[str, Any],
    submission_end_at: Optional[datetime],
    completion_at: Optional[datetime],
    now: datetime,
) -> Tuple[Dict[str, Any], Optional[datetime]]:
    metric = {
        'started_at': None,
        'ended_at': None,
        'duration_seconds': None,
        'source': METRIC_SOURCE_UNAVAILABLE,
    }
    has_reference = bool(str(batch.get('uipath_reference') or '').strip())
    if not has_reference and not progress_timestamps.get('first_progress_at'):
        return metric, None

    started_at = submission_end_at or progress_timestamps.get('earliest_created_at')
    if not started_at:
        started_at = progress_timestamps.get('earliest_non_queued_updated_at')

    ended_at = progress_timestamps.get('latest_non_queued_updated_at')
    batch_status = str(batch.get('status') or '').strip().lower()
    if not ended_at and started_at and batch_status in {'submitting', 'running'}:
        ended_at = now
    if not ended_at and started_at and completion_at:
        ended_at = completion_at

    if not started_at or not ended_at:
        return metric, None

    metric['started_at'] = started_at.isoformat()
    metric['ended_at'] = ended_at.isoformat()
    metric['duration_seconds'] = max(
        0,
        int(round((ended_at - started_at).total_seconds())),
    )
    metric['source'] = METRIC_SOURCE_ESTIMATED
    return metric, ended_at


def _build_total_metric(
    batch: Dict[str, Any],
    submission_end_at: Optional[datetime],
    extraction_end_at: Optional[datetime],
    completion_at: Optional[datetime],
    submission_source: Optional[str],
    completion_source: Optional[str],
    now: datetime,
) -> Dict[str, Any]:
    submitted_at = parse_iso_datetime(batch.get('submitted_at'))
    metric = {
        'started_at': submitted_at.isoformat() if submitted_at else None,
        'ended_at': None,
        'duration_seconds': None,
        'source': METRIC_SOURCE_UNAVAILABLE,
    }
    if not submitted_at:
        return metric

    ended_at: Optional[datetime] = None
    source = METRIC_SOURCE_UNAVAILABLE
    batch_status = str(batch.get('status') or '').strip().lower()

    if completion_at:
        ended_at = completion_at
        source = completion_source or METRIC_SOURCE_EXACT
    elif extraction_end_at:
        ended_at = extraction_end_at
        source = METRIC_SOURCE_ESTIMATED
    elif batch_status in {'submitting', 'running'}:
        ended_at = now
        source = METRIC_SOURCE_EXACT
    elif submission_end_at:
        ended_at = submission_end_at
        source = submission_source or METRIC_SOURCE_ESTIMATED

    if not ended_at:
        return metric

    metric['ended_at'] = ended_at.isoformat()
    metric['duration_seconds'] = max(
        0,
        int(round((ended_at - submitted_at).total_seconds())),
    )
    metric['source'] = source
    return metric


def _build_throughput_metric(
    status_counts: Any,
    extraction_metric: Dict[str, Any],
) -> Dict[str, Any]:
    if not isinstance(status_counts, dict):
        status_counts = {}

    processed_files = (
        int(status_counts.get('extracted', 0) or 0)
        + int(status_counts.get('failed', 0) or 0)
        + int(status_counts.get('exported', 0) or 0)
    )
    metric = {
        'processed_files': processed_files,
        'files_per_minute': None,
        'source': METRIC_SOURCE_UNAVAILABLE,
    }

    duration_seconds = _coerce_duration_seconds(
        extraction_metric.get('duration_seconds')
        if isinstance(extraction_metric, dict)
        else None
    )
    if duration_seconds is None or duration_seconds <= 0:
        return metric

    metric['files_per_minute'] = round(processed_files / (duration_seconds / 60.0), 1)
    metric['source'] = str(
        extraction_metric.get('source')
        if isinstance(extraction_metric, dict)
        else METRIC_SOURCE_ESTIMATED
    )
    return metric
