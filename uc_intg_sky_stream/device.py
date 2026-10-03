"""Sky Stream device - maintains a bound RICS connection to one Sky box.

The box is a device the user powers off (standby), so it follows the TV-off
pattern: ``establish_connection()`` never raises when the box is unreachable -
the entities report OFF instead of going unavailable, and ``power_on()`` wakes
the box with Wake-on-LAN. Reachability (a TCP probe) drives ON/OFF state; the
bound WebSocket is (re)established lazily and reused for the box's lifetime.

Key commands share one WebSocket and each waits for its own reply, so they are
sent one at a time. Failed binds back off, because repeated failed binds can
lock the box out.
"""

import asyncio
import logging
import time
from typing import Any

from ucapi_framework import PollingDevice

from uc_intg_sky_stream.client import (
    SkyRemoteClient,
    is_box_reachable,
    send_wol,
)
from uc_intg_sky_stream.config import SkyStreamConfig
from uc_intg_sky_stream.const import (
    KEY_CHANNEL_DOWN,
    KEY_CHANNEL_UP,
    KEY_FAST_FORWARD,
    KEY_MUTE,
    KEY_PLAY_PAUSE,
    KEY_POWER,
    KEY_REWIND,
    KEY_VOLUME_DOWN,
    KEY_VOLUME_UP,
    STATE_OFF,
    STATE_ON,
)

_LOG = logging.getLogger(__name__)

_WAKE_POLL_ATTEMPTS = 15
_WAKE_POLL_INTERVAL = 2.0
_BIND_BACKOFF_START = 30.0  # seconds after the first failed bind, doubling
_BIND_BACKOFF_MAX = 900.0
_BIND_USER_MIN_GAP = 10.0  # a button press may retry a failed bind this often


class SkyStreamDevice(PollingDevice):
    """One Sky Stream / Sky Glass set-top box."""

    def __init__(self, device_config: SkyStreamConfig, **kwargs: Any) -> None:
        super().__init__(device_config, poll_interval=30, **kwargs)
        self._device_config = device_config
        self._client: SkyRemoteClient | None = None
        self._connect_lock: asyncio.Lock = asyncio.Lock()
        self._send_lock: asyncio.Lock = asyncio.Lock()  # one key command in flight
        self._state: str = STATE_OFF
        self._bind_failures: int = 0
        self._last_bind_attempt: float = 0.0

    # -- identity ------------------------------------------------------
    @property
    def identifier(self) -> str:
        return self._device_config.identifier

    @property
    def name(self) -> str:
        return self._device_config.name

    @property
    def address(self) -> str:
        return self._device_config.host

    @property
    def log_id(self) -> str:
        return f"{self.name} ({self.address})"

    @property
    def state(self) -> str:
        return self._state

    # -- connection lifecycle (TV-off pattern, rule 14) ---------------
    async def establish_connection(self) -> SkyRemoteClient:
        async with self._connect_lock:
            if self._client is None:
                self._client = SkyRemoteClient(self._device_config.host, self._device_config.port)

        if await is_box_reachable(self._device_config.host, self._device_config.port):
            await self._ensure_bound()
            self._state = STATE_ON if (self._client and self._client.connected) else STATE_OFF
        else:
            self._state = STATE_OFF
        return self._client

    def _bind_allowed(self, user: bool) -> bool:
        """After failed binds, wait before trying again (the box can lock out a client)."""
        if not self._bind_failures:
            return True
        since = time.monotonic() - self._last_bind_attempt
        if user:
            return since >= _BIND_USER_MIN_GAP
        wait = min(_BIND_BACKOFF_START * 2 ** (self._bind_failures - 1), _BIND_BACKOFF_MAX)
        return since >= wait

    async def _ensure_bound(self, user: bool = False) -> bool:
        """Ensure the client is connected and bound. Returns success."""
        async with self._connect_lock:
            if self._client is None:
                return False
            if self._client.connected:
                return True
            if not self._bind_allowed(user):
                _LOG.debug("[%s] Bind skipped (backing off after %d failures)", self.log_id, self._bind_failures)
                return False
            self._last_bind_attempt = time.monotonic()
            try:
                await self._client.disconnect()
                await self._client.connect_and_bind()
                if self._bind_failures:
                    _LOG.info("[%s] Bound again after %d failed attempts", self.log_id, self._bind_failures)
                self._bind_failures = 0
                return True
            except Exception as err:  # pylint: disable=broad-exception-caught
                self._bind_failures += 1
                log = _LOG.warning if self._bind_failures in (1, 5) else _LOG.debug
                log("[%s] Bind failed (%d): %s", self.log_id, self._bind_failures, err)
                return False

    async def poll_device(self) -> None:
        reachable = await is_box_reachable(self._device_config.host, self._device_config.port)
        if reachable and self._client is not None and not self._client.connected:
            await self._ensure_bound()
        self._state = STATE_ON if reachable else STATE_OFF
        self.push_update()

    async def disconnect(self) -> None:
        async with self._connect_lock:
            if self._client is not None:
                await self._client.disconnect()
                self._client = None
        self._state = STATE_OFF
        await super().disconnect()

    # -- commands ------------------------------------------------------
    async def send_key(self, key: str) -> bool:
        """Send a key command, reconnecting once on failure."""
        async with self._send_lock:
            return await self._send_key_locked(key)

    async def _send_key_locked(self, key: str) -> bool:
        if self._client is None:
            self._client = SkyRemoteClient(self._device_config.host, self._device_config.port)
        if not self._client.connected and not await is_box_reachable(
            self._device_config.host, self._device_config.port
        ):
            # Box off or gone: answer at once instead of two 10 s connect timeouts per press.
            _LOG.warning("[%s] Cannot send %s - box not reachable", self.log_id, key)
            return False
        for attempt in range(2):
            if not self._client.connected and not await self._ensure_bound(user=True):
                _LOG.warning("[%s] Cannot send %s - pairing with the box failed", self.log_id, key)
                return False
            try:
                resp = await self._client.send_key(key)
                if not resp.get("status", False):
                    _LOG.warning("[%s] Key %s rejected: %s", self.log_id, key, resp)
                self._state = STATE_ON
                return bool(resp.get("status", False))
            except Exception as err:  # pylint: disable=broad-exception-caught
                _LOG.debug("[%s] send_key(%s) attempt %d failed: %s", self.log_id, key, attempt + 1, err)
                await self._client.disconnect()
        return False

    async def power_on(self) -> bool:
        """Wake the box (WoL if a MAC is known), then ensure it is out of standby."""
        reachable = await is_box_reachable(self._device_config.host, self._device_config.port)
        if not reachable and self._device_config.mac:
            _LOG.info("[%s] Sending Wake-on-LAN to %s", self.log_id, self._device_config.mac)
            try:
                send_wol(self._device_config.mac)
            except ValueError as err:
                _LOG.warning("[%s] WoL failed: %s", self.log_id, err)
            for _ in range(_WAKE_POLL_ATTEMPTS):
                await asyncio.sleep(_WAKE_POLL_INTERVAL)
                if await is_box_reachable(self._device_config.host, self._device_config.port):
                    reachable = True
                    break
        elif not reachable:
            _LOG.warning("[%s] Box not reachable and no MAC address known for Wake-on-LAN", self.log_id)

        ok = False
        if reachable and await self._ensure_bound(user=True):
            # Power is a toggle; only press it if the box was asleep.
            if self._state != STATE_ON:
                ok = await self.send_key(KEY_POWER)
            else:
                ok = True
            self._state = STATE_ON
        self.push_update()
        return ok

    async def power_off(self) -> bool:
        """Put the box into standby (Power toggle) if it is currently on."""
        ok = True
        if await is_box_reachable(self._device_config.host, self._device_config.port):
            ok = await self.send_key(KEY_POWER)
        self._state = STATE_OFF
        self.push_update()
        return ok

    async def power_toggle(self) -> bool:
        return await self.send_key(KEY_POWER)

    async def volume_up(self) -> bool:
        return await self.send_key(KEY_VOLUME_UP)

    async def volume_down(self) -> bool:
        return await self.send_key(KEY_VOLUME_DOWN)

    async def mute_toggle(self) -> bool:
        return await self.send_key(KEY_MUTE)

    async def play_pause(self) -> bool:
        return await self.send_key(KEY_PLAY_PAUSE)

    async def fast_forward(self) -> bool:
        return await self.send_key(KEY_FAST_FORWARD)

    async def rewind(self) -> bool:
        return await self.send_key(KEY_REWIND)

    async def channel_up(self) -> bool:
        return await self.send_key(KEY_CHANNEL_UP)

    async def channel_down(self) -> bool:
        return await self.send_key(KEY_CHANNEL_DOWN)
