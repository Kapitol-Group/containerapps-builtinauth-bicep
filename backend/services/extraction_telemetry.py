from __future__ import annotations

import logging
import os
import threading
from typing import Dict, Optional

logger = logging.getLogger(__name__)

_configure_lock = threading.Lock()
_configured = False


def configure_process_telemetry(service_name: str) -> bool:
    global _configured

    connection_string = os.getenv('APPLICATIONINSIGHTS_CONNECTION_STRING', '').strip()
    if not connection_string:
        return False

    with _configure_lock:
        if _configured:
            return True
        try:
            from azure.monitor.opentelemetry import configure_azure_monitor
        except ImportError:
            logger.warning(
                "APPLICATIONINSIGHTS_CONNECTION_STRING is set, but "
                "azure-monitor-opentelemetry is not installed."
            )
            return False

        os.environ.setdefault('OTEL_SERVICE_NAME', service_name)
        configure_azure_monitor(connection_string=connection_string)
        _configured = True
        return True


class ExtractionTelemetry:
    """Structured extraction telemetry with optional Azure Monitor export."""

    def __init__(self, service_name: str):
        self.enabled = configure_process_telemetry(service_name)
        self._meter = None
        self._enqueued_counter = None
        self._dequeued_counter = None
        self._model_failure_counter = None
        self._token_counter = None
        self._batch_completion_counter = None
        self._file_latency_histogram = None

        if not self.enabled:
            return

        try:
            from opentelemetry import metrics

            self._meter = metrics.get_meter("kapitol_tender_automation.extraction")
            self._enqueued_counter = self._meter.create_counter(
                "drawing_extraction_enqueued",
                unit="1",
                description="Count of extraction batches enqueued",
            )
            self._dequeued_counter = self._meter.create_counter(
                "drawing_extraction_dequeued",
                unit="1",
                description="Count of extraction batches dequeued",
            )
            self._model_failure_counter = self._meter.create_counter(
                "drawing_extraction_model_failures",
                unit="1",
                description="Count of vision extraction failures",
            )
            self._token_counter = self._meter.create_counter(
                "drawing_extraction_tokens",
                unit="1",
                description="Azure OpenAI token usage",
            )
            self._batch_completion_counter = self._meter.create_counter(
                "drawing_extraction_batch_completions",
                unit="1",
                description="Completed extraction batches",
            )
            self._file_latency_histogram = self._meter.create_histogram(
                "drawing_extraction_file_latency_ms",
                unit="ms",
                description="Per-file extraction latency",
            )
        except Exception:
            logger.exception("Failed to initialize extraction telemetry meter")
            self.enabled = False

    def _log(self, event_name: str, attributes: Dict[str, object]) -> None:
        fields = ' '.join(f"{key}={value}" for key, value in attributes.items())
        logger.info("telemetry_event=%s %s", event_name, fields)

    def record_enqueue(self, *, tender_id: str, batch_id: str, file_count: int) -> None:
        attributes = {'tender_id': tender_id, 'batch_id': batch_id, 'file_count': file_count}
        self._log('enqueue', attributes)
        if self._enqueued_counter:
            self._enqueued_counter.add(1, attributes)

    def record_dequeue(
        self,
        *,
        tender_id: str,
        batch_id: str,
        dequeue_count: int,
    ) -> None:
        attributes = {
            'tender_id': tender_id,
            'batch_id': batch_id,
            'dequeue_count': dequeue_count,
        }
        self._log('dequeue', attributes)
        if self._dequeued_counter:
            self._dequeued_counter.add(1, attributes)

    def record_file_latency(
        self,
        *,
        tender_id: str,
        batch_id: str,
        file_path: str,
        latency_ms: float,
    ) -> None:
        attributes = {'tender_id': tender_id, 'batch_id': batch_id, 'file_path': file_path}
        self._log('file_latency', {**attributes, 'latency_ms': round(latency_ms, 2)})
        if self._file_latency_histogram:
            self._file_latency_histogram.record(latency_ms, attributes)

    def record_model_failure(
        self,
        *,
        tender_id: str,
        batch_id: str,
        reason: str,
    ) -> None:
        attributes = {'tender_id': tender_id, 'batch_id': batch_id, 'reason': reason}
        self._log('model_failure', attributes)
        if self._model_failure_counter:
            self._model_failure_counter.add(1, attributes)

    def record_token_usage(
        self,
        *,
        tender_id: str,
        batch_id: str,
        total_tokens: Optional[int],
    ) -> None:
        if not total_tokens:
            return
        attributes = {'tender_id': tender_id, 'batch_id': batch_id}
        self._log('token_usage', {**attributes, 'total_tokens': total_tokens})
        if self._token_counter:
            self._token_counter.add(total_tokens, attributes)

    def record_batch_completion(
        self,
        *,
        tender_id: str,
        batch_id: str,
        status: str,
    ) -> None:
        attributes = {'tender_id': tender_id, 'batch_id': batch_id, 'status': status}
        self._log('batch_completion', attributes)
        if self._batch_completion_counter:
            self._batch_completion_counter.add(1, attributes)

