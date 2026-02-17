"""Azure Event Hub client — drop-in alternative to MqttClient.

Implements the same async ``publish(topic, payload)`` interface so that
``BaseStream`` can target either MQTT or Event Hub without changes.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from .config import EventHubConfig

logger = logging.getLogger(__name__)

# Lazy-import the SDK so the rest of the simulator can run without
# azure-eventhub installed when outputMode == "mqtt".
_EventHubProducerClient = None
_EventData = None
_DefaultAzureCredential = None


def _ensure_sdk() -> None:
    """Import azure-eventhub (and azure-identity) on first use."""
    global _EventHubProducerClient, _EventData, _DefaultAzureCredential  # noqa: PLW0603
    if _EventHubProducerClient is not None:
        return

    try:
        from azure.eventhub.aio import EventHubProducerClient
        from azure.eventhub import EventData
        _EventHubProducerClient = EventHubProducerClient
        _EventData = EventData
    except ImportError as exc:
        raise ImportError(
            "azure-eventhub is required when outputMode is 'eventHub'. "
            "Install it with:  pip install azure-eventhub"
        ) from exc

    try:
        from azure.identity.aio import DefaultAzureCredential
        _DefaultAzureCredential = DefaultAzureCredential
    except ImportError:
        # Only needed for managedIdentity / defaultCredential auth
        _DefaultAzureCredential = None


class EventHubClient:
    """Async-friendly Azure Event Hub producer with the same publish() API as MqttClient."""

    def __init__(self, cfg: EventHubConfig) -> None:
        _ensure_sdk()
        self._cfg = cfg
        self._producer = None
        self._credential = None
        self._msg_count = 0
        self._pending: list = []
        self._pending_lock = asyncio.Lock()
        self._flush_task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Create the EventHubProducerClient."""
        if self._cfg.credential in ("managedIdentity", "defaultCredential"):
            if _DefaultAzureCredential is None:
                raise ImportError(
                    "azure-identity is required for defaultCredential / managedIdentity. "
                    "Install it with:  pip install azure-identity"
                )
            self._credential = _DefaultAzureCredential()
            self._producer = _EventHubProducerClient(
                fully_qualified_namespace=self._cfg.fully_qualified_namespace,
                eventhub_name=self._cfg.eventhub_name,
                credential=self._credential,
            )
            logger.info(
                "Event Hub connected (%s) — %s/%s",
                self._cfg.credential,
                self._cfg.fully_qualified_namespace,
                self._cfg.eventhub_name,
            )
        else:
            # Connection string auth
            self._producer = _EventHubProducerClient.from_connection_string(
                conn_str=self._cfg.connection_string,
                eventhub_name=self._cfg.eventhub_name,
            )
            logger.info(
                "Event Hub connected (connection string) — %s",
                self._cfg.eventhub_name,
            )

        # Start background flush loop
        self._flush_task = asyncio.create_task(
            self._flush_loop(), name="eventhub-flush"
        )

    async def disconnect(self) -> None:
        """Flush remaining events and close."""
        # Flush remaining events first (before cancelling flush loop)
        async with self._pending_lock:
            await self._flush_pending()

        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        if self._producer:
            await self._producer.close()
            logger.info(
                "Event Hub disconnected (sent %d events total)", self._msg_count
            )

        if self._credential and hasattr(self._credential, "close"):
            await self._credential.close()

    # ------------------------------------------------------------------
    # Publishing — same signature as MqttClient.publish()
    # ------------------------------------------------------------------

    async def publish(
        self,
        topic: str,
        payload: dict[str, Any],
        *,
        qos: int | None = None,     # ignored — kept for API compat
        retain: bool = False,        # ignored — kept for API compat
    ) -> None:
        """Send a JSON event to Event Hub.

        The MQTT ``topic`` is preserved as an Event Hub *property* so
        downstream consumers can route / filter by it.
        """
        if self._producer is None:
            raise RuntimeError("EventHubClient not connected")

        data = json.dumps(payload, default=str)
        event = _EventData(data)  # type: ignore[misc]
        event.properties = {"mqtt_topic": topic}

        async with self._pending_lock:
            self._pending.append(event)
            if len(self._pending) >= self._cfg.max_batch_size:
                await self._flush_pending()

    def subscribe(
        self,
        topic: str,
        *,
        qos: int = 1,
        callback: Any = None,
    ) -> None:
        """No-op — Event Hub producer does not support subscriptions."""
        logger.debug(
            "subscribe() called on EventHubClient (no-op) — topic=%s", topic
        )

    @property
    def is_connected(self) -> bool:
        return self._producer is not None

    @property
    def message_count(self) -> int:
        return self._msg_count

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _resolve_partition_key(self, topic: str, payload: dict) -> str | None:
        mode = self._cfg.partition_key_mode
        if mode == "topic":
            return topic
        if mode == "stream":
            return payload.get("stream", topic.split("/")[-1])
        return None  # round-robin

    async def _flush_loop(self) -> None:
        """Periodically flush pending events so they don't sit too long."""
        interval = self._cfg.max_wait_time_sec
        while True:
            await asyncio.sleep(interval)
            async with self._pending_lock:
                await self._flush_pending()

    async def _flush_pending(self) -> None:
        """Send all pending events as a batch. Caller must hold _pending_lock."""
        if not self._pending or self._producer is None:
            return
        count = len(self._pending)
        try:
            batch = await self._producer.create_batch()
            sent = 0
            while self._pending:
                ev = self._pending[0]
                try:
                    batch.add(ev)
                    self._pending.pop(0)
                except ValueError:
                    # Batch full — send what we have, start a new one
                    await self._producer.send_batch(batch)
                    sent += 1
                    batch = await self._producer.create_batch()
                    # Don't pop — retry this event in the new batch
            if batch.size_in_bytes > 0:
                await self._producer.send_batch(batch)
            self._msg_count += count
            logger.debug("Flushed %d events to Event Hub", count)
        except Exception as exc:
            logger.error("Event Hub send failed (%d events may be lost): %s", len(self._pending), exc)
            self._pending.clear()  # drop to avoid infinite retry
