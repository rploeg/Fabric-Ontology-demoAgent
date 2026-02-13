"""MQTT client wrapper with reconnect, TLS, and SAT auth support."""

from __future__ import annotations

import asyncio
import json
import logging
import ssl
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import paho.mqtt.client as mqtt

from .config import MqttConfig

logger = logging.getLogger(__name__)

# Kubernetes-mounted SAT token path
_SAT_TOKEN_PATH = Path("/var/run/secrets/tokens/mqtt-client-token")


class MqttClient:
    """Thin async-friendly wrapper around paho-mqtt v2."""

    def __init__(self, cfg: MqttConfig) -> None:
        self._cfg = cfg
        self._client: mqtt.Client | None = None
        self._connected = asyncio.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._msg_count = 0
        self._subscriptions: Dict[str, Callable[[str], None]] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Create the paho client and initiate the connection."""
        self._loop = asyncio.get_running_loop()

        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=self._cfg.client_id,
            protocol=mqtt.MQTTv5,
        )

        # --- Auth ---
        if self._cfg.auth_method == "serviceAccountToken":
            token = self._read_sat_token()
            if token:
                self._client.username_pw_set(username="K8S-SAT", password=token)
                logger.info("Using Service Account Token authentication")
            else:
                logger.warning("SAT token not found — falling back to no auth")
        elif self._cfg.auth_method == "usernamePassword":
            self._client.username_pw_set(
                username=self._cfg.username,
                password=self._cfg.password,
            )
            logger.info("Using username/password authentication")
        else:
            logger.info("Using no authentication")

        # --- TLS ---
        if self._cfg.use_tls:
            ctx = ssl.create_default_context()
            self._client.tls_set_context(ctx)
            logger.info("TLS enabled")

        # --- Callbacks ---
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

        # Non-blocking loop
        self._client.connect_async(self._cfg.broker, self._cfg.port, self._cfg.keep_alive)
        self._client.loop_start()

        # Wait for the first connection
        try:
            await asyncio.wait_for(self._connected.wait(), timeout=15)
        except asyncio.TimeoutError:
            logger.error(
                "Timed out connecting to %s:%s — will keep retrying in background",
                self._cfg.broker,
                self._cfg.port,
            )

    async def disconnect(self) -> None:
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            logger.info("Disconnected from MQTT broker (published %d messages total)", self._msg_count)

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    async def publish(
        self,
        topic: str,
        payload: dict[str, Any],
        *,
        qos: int | None = None,
        retain: bool = False,
    ) -> None:
        """Publish a JSON payload to `topic`."""
        if self._client is None:
            raise RuntimeError("MqttClient not connected")

        data = json.dumps(payload, default=str)
        q = qos if qos is not None else self._cfg.qos

        info = self._client.publish(topic, data, qos=q, retain=retain)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            logger.warning("Publish failed (rc=%s) on topic %s", info.rc, topic)
        else:
            self._msg_count += 1

    def subscribe(
        self,
        topic: str,
        *,
        qos: int = 1,
        callback: Callable[[str], None] | None = None,
    ) -> None:
        """Subscribe to a topic. Messages are passed to *callback* as raw strings."""
        if self._client is None:
            raise RuntimeError("MqttClient not connected")
        if callback:
            self._subscriptions[topic] = callback
        self._client.subscribe(topic, qos=qos)
        logger.info("Subscribed to %s (qos=%d)", topic, qos)

    @property
    def is_connected(self) -> bool:
        return self._connected.is_set()

    @property
    def message_count(self) -> int:
        return self._msg_count

    # ------------------------------------------------------------------
    # Internal callbacks
    # ------------------------------------------------------------------

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: mqtt.ConnectFlags,
        rc: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ) -> None:
        if rc.is_failure:
            logger.error("Connection refused: %s", rc)
        else:
            logger.info("Connected to MQTT broker %s:%s", self._cfg.broker, self._cfg.port)
            if self._loop:
                self._loop.call_soon_threadsafe(self._connected.set)

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: mqtt.DisconnectFlags,
        rc: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ) -> None:
        logger.warning("Disconnected (rc=%s) — paho will auto-reconnect", rc)
        if self._loop:
            self._loop.call_soon_threadsafe(self._connected.clear)

    def _on_message(
        self,
        client: mqtt.Client,
        userdata: Any,
        msg: mqtt.MQTTMessage,
    ) -> None:
        """Dispatch incoming messages to registered callbacks."""
        topic = msg.topic
        payload_str = msg.payload.decode("utf-8", errors="replace")
        cb = self._subscriptions.get(topic)
        if cb:
            try:
                cb(payload_str)
            except Exception as exc:
                logger.error("Subscription callback error on %s: %s", topic, exc)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _read_sat_token() -> str | None:
        if _SAT_TOKEN_PATH.exists():
            return _SAT_TOKEN_PATH.read_text().strip()
        return None
