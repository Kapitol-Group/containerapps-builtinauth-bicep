from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Iterable, List, Optional

from azure.identity import DefaultAzureCredential
from azure.storage.queue import QueueClient, QueueMessage, QueueServiceClient

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExtractionBatchMessage:
    tender_id: str
    batch_id: str
    reference: str

    def to_json(self) -> str:
        return json.dumps(
            {
                'tender_id': self.tender_id,
                'batch_id': self.batch_id,
                'reference': self.reference,
            },
            separators=(',', ':'),
        )

    @classmethod
    def from_json(cls, payload: str) -> "ExtractionBatchMessage":
        data = json.loads(payload)
        return cls(
            tender_id=str(data['tender_id']),
            batch_id=str(data['batch_id']),
            reference=str(data['reference']),
        )


class ExtractionQueueService:
    """Azure Storage Queue wrapper for batch-scoped extraction work."""

    def __init__(self, account_name: str, queue_name: str):
        self.account_name = (account_name or '').strip()
        self.queue_name = (queue_name or '').strip()
        self.queue_client: Optional[QueueClient] = None

        if not self.account_name or not self.queue_name:
            logger.warning(
                "Extraction queue is not configured "
                "(account_name=%s, queue_name=%s)",
                bool(self.account_name),
                bool(self.queue_name),
            )
            return

        service_client = QueueServiceClient(
            account_url=f"https://{self.account_name}.queue.core.windows.net",
            credential=DefaultAzureCredential(),
        )
        self.queue_client = service_client.get_queue_client(self.queue_name)

    @property
    def is_configured(self) -> bool:
        return self.queue_client is not None

    def enqueue_batch(self, message: ExtractionBatchMessage) -> QueueMessage:
        if self.queue_client is None:
            raise RuntimeError("Extraction queue is not configured")
        queue_message = self.queue_client.send_message(message.to_json())
        logger.info(
            "Enqueued extraction batch tender_id=%s batch_id=%s reference=%s",
            message.tender_id,
            message.batch_id,
            message.reference,
        )
        return queue_message

    def receive_messages(
        self,
        *,
        max_messages: int,
        visibility_timeout: int,
    ) -> List[QueueMessage]:
        if self.queue_client is None:
            raise RuntimeError("Extraction queue is not configured")
        received: Iterable[QueueMessage] = self.queue_client.receive_messages(
            max_messages=max_messages,
            messages_per_page=max_messages,
            visibility_timeout=visibility_timeout,
        )
        return list(received)

    def delete_message(self, message: QueueMessage) -> None:
        if self.queue_client is None:
            raise RuntimeError("Extraction queue is not configured")
        self.queue_client.delete_message(message)

