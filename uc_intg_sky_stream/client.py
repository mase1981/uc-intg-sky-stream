"""Sky Remote (RICS) protocol client.

Implements the LAN control protocol used by the Sky Remote app to drive Sky
Stream / Sky Glass boxes: mTLS on TCP 8091, a manual WebSocket upgrade to
``/iptarget``, then Pair -> derive auth token -> Bind -> ``keyatomic`` key
commands. The WebSocket framing is done by hand (no third-party ws library) so
the only runtime dependency is the Python standard library.

Ported from the reverse-engineered protocol reference at
https://github.com/jatatech/sky_stream_remote and adapted for the async
ucapi-framework device model.
"""

import asyncio
import base64
import hashlib
import json
import logging
import os
import socket
import ssl
import struct
import tempfile
import uuid

from uc_intg_sky_stream.certs import CERT_CHAIN_PEM, PRIVATE_KEY_PEM
from uc_intg_sky_stream.const import AUTH_SALT, DEFAULT_PORT

_LOG = logging.getLogger(__name__)

_OP_TEXT = 0x1
_OP_CLOSE = 0x8
_OP_PING = 0x9
_OP_PONG = 0xA


class SkyRemoteError(Exception):
    """Base exception for Sky Remote errors."""


class SkyRemoteConnectionError(SkyRemoteError):
    """Connection failed."""


class SkyRemoteAuthError(SkyRemoteError):
    """Authentication (pair/bind) failed."""


def send_wol(mac_address: str) -> None:
    """Send a Wake-on-LAN magic packet to a MAC address (broadcast, UDP 9)."""
    mac = mac_address.replace(":", "").replace("-", "").replace(".", "")
    if len(mac) != 12:
        raise ValueError(f"Invalid MAC address: {mac_address}")
    magic = b"\xff" * 6 + bytes.fromhex(mac) * 16
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        for port in (9, 7):
            try:
                sock.sendto(magic, ("255.255.255.255", port))
            except OSError as err:  # pylint: disable=broad-exception-caught
                _LOG.debug("WoL send on port %s failed: %s", port, err)


async def is_box_reachable(host: str, port: int = DEFAULT_PORT, timeout: float = 1.5) -> bool:
    """Quick TCP probe: True if the box is awake and accepting connections."""
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:  # pylint: disable=broad-exception-caught
            pass
        return True
    except (OSError, asyncio.TimeoutError):
        return False


def compute_authtoken(cert_fingerprint: str, pairingcode: str, controllernonce: str, stbnonce: str) -> str:
    """Derive the Bind Request auth token (two-stage SHA-256).

    inner = SHA256( hex_decode(cert_fingerprint) || pairingcode || controllernonce )
    token = Base64( SHA256( stbnonce || inner || "biT43y" ) )
    """
    stage1 = hashlib.sha256(
        bytes.fromhex(cert_fingerprint)
        + pairingcode.encode("utf-8")
        + controllernonce.encode("utf-8")
    ).digest()
    stage2 = hashlib.sha256(stbnonce.encode("utf-8") + stage1 + AUTH_SALT).digest()
    return base64.b64encode(stage2).decode("utf-8")


def _compute_cert_fingerprint(cert_chain_pem: str) -> str:
    """SHA-256 hex of the leaf client certificate DER."""
    marker_begin = "-----BEGIN CERTIFICATE-----"
    marker_end = "-----END CERTIFICATE-----"
    start = cert_chain_pem.index(marker_begin) + len(marker_begin)
    end = cert_chain_pem.index(marker_end)
    leaf_der = base64.b64decode(cert_chain_pem[start:end].replace("\n", "").replace("\r", ""))
    return hashlib.sha256(leaf_der).hexdigest()


def _create_ssl_context() -> ssl.SSLContext:
    """SSL context loaded with the embedded mTLS client identity."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.set_alpn_protocols(["http/1.1"])

    cert_file = tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False, encoding="utf-8")
    key_file = tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False, encoding="utf-8")
    try:
        cert_file.write(CERT_CHAIN_PEM)
        cert_file.close()
        key_file.write(PRIVATE_KEY_PEM)
        key_file.close()
        ctx.load_cert_chain(certfile=cert_file.name, keyfile=key_file.name)
    finally:
        for path in (cert_file.name, key_file.name):
            try:
                os.unlink(path)
            except OSError:
                pass
    return ctx


# Computed once at import - the embedded identity never changes.
_CERT_FINGERPRINT = _compute_cert_fingerprint(CERT_CHAIN_PEM)
_SSL_CONTEXT = _create_ssl_context()


def _ws_mask(data: bytes, mask_key: bytes) -> bytes:
    return bytes(b ^ mask_key[i % 4] for i, b in enumerate(data))


def _build_ws_frame(payload: bytes, opcode: int = _OP_TEXT) -> bytes:
    """Build a client -> server WebSocket frame (always masked)."""
    mask_key = os.urandom(4)
    header = bytes([0x80 | opcode])
    length = len(payload)
    if length < 126:
        header += bytes([0x80 | length])
    elif length < 65536:
        header += bytes([0x80 | 126]) + struct.pack("!H", length)
    else:
        header += bytes([0x80 | 127]) + struct.pack("!Q", length)
    return header + mask_key + _ws_mask(payload, mask_key)


async def _read_ws_frame(reader: asyncio.StreamReader) -> tuple[int, bytes]:
    head = await reader.readexactly(2)
    opcode = head[0] & 0x0F
    masked = bool(head[1] & 0x80)
    length = head[1] & 0x7F
    if length == 126:
        length = struct.unpack("!H", await reader.readexactly(2))[0]
    elif length == 127:
        length = struct.unpack("!Q", await reader.readexactly(8))[0]
    if masked:
        mask_key = await reader.readexactly(4)
        payload = _ws_mask(await reader.readexactly(length), mask_key)
    else:
        payload = await reader.readexactly(length)
    return opcode, payload


class SkyRemoteClient:
    """Async client for the Sky STB RICS protocol (one connection lifetime)."""

    def __init__(self, host: str, port: int = DEFAULT_PORT) -> None:
        self.host = host
        self.port = port
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self.tid: str = str(uuid.uuid4())
        self.controllernonce: str = str(uuid.uuid4())
        self.bind_id: int | None = None
        self.authtoken: str | None = None
        self.device_name: str | None = None
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected and self._writer is not None and self.bind_id is not None

    async def connect(self) -> None:
        """Open the mTLS WebSocket connection (SNI sky.xcal.tv, path /iptarget)."""
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(
                    self.host, self.port, ssl=_SSL_CONTEXT, server_hostname="sky.xcal.tv"
                ),
                timeout=10,
            )

            ws_key = base64.b64encode(os.urandom(16)).decode()
            upgrade = (
                f"GET /iptarget HTTP/1.1\r\n"
                f"Host: sky.xcal.tv:{self.port}\r\n"
                f"Upgrade: websocket\r\n"
                f"Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {ws_key}\r\n"
                f"Sec-WebSocket-Version: 13\r\n"
                f"Origin: https://{self.host}:{self.port}/\r\n"
                f"User-Agent: Dart/3.9 (dart:io)\r\n"
                f"Cache-Control: no-cache\r\n"
                f"Accept-Encoding: gzip\r\n"
                f"\r\n"
            )
            self._writer.write(upgrade.encode())
            await self._writer.drain()

            response = b""
            while b"\r\n\r\n" not in response:
                chunk = await asyncio.wait_for(self._reader.read(4096), timeout=10)
                if not chunk:
                    raise SkyRemoteConnectionError("Connection closed during handshake")
                response += chunk

            status_line = response.split(b"\r\n")[0].decode(errors="replace")
            if "101" not in status_line:
                raise SkyRemoteConnectionError(f"WebSocket upgrade failed: {status_line}")

            self._connected = True
            _LOG.debug("WebSocket connected to %s:%s", self.host, self.port)
        except SkyRemoteConnectionError:
            self._connected = False
            raise
        except Exception as err:  # pylint: disable=broad-exception-caught
            self._connected = False
            raise SkyRemoteConnectionError(f"Failed to connect to {self.host}:{self.port}: {err}") from err

    async def disconnect(self) -> None:
        """Close the WebSocket connection."""
        self._connected = False
        self.bind_id = None
        self.authtoken = None
        if self._writer:
            try:
                self._writer.write(_build_ws_frame(b"", _OP_CLOSE))
                await self._writer.drain()
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:  # pylint: disable=broad-exception-caught
                pass
            self._writer = None
            self._reader = None

    async def _send(self, msg: dict) -> None:
        if not self._writer or not self._connected:
            raise SkyRemoteConnectionError("Not connected")
        try:
            self._writer.write(_build_ws_frame(json.dumps(msg).encode("utf-8"), _OP_TEXT))
            await self._writer.drain()
        except (ConnectionResetError, OSError, BrokenPipeError) as err:
            self._connected = False
            raise SkyRemoteConnectionError(f"Connection lost: {err}") from err

    async def _recv(self, timeout: float = 10.0) -> dict:
        if not self._reader or not self._connected:
            raise SkyRemoteConnectionError("Not connected")
        try:
            while True:
                opcode, payload = await asyncio.wait_for(_read_ws_frame(self._reader), timeout=timeout)
                if opcode == _OP_TEXT:
                    return json.loads(payload.decode("utf-8"))
                if opcode == _OP_PING:
                    if self._writer:
                        self._writer.write(_build_ws_frame(payload, _OP_PONG))
                        await self._writer.drain()
                    continue
                if opcode == _OP_CLOSE:
                    self._connected = False
                    raise SkyRemoteConnectionError("WebSocket closed by server")
        except (ConnectionResetError, OSError, BrokenPipeError) as err:
            self._connected = False
            raise SkyRemoteConnectionError(f"Connection lost: {err}") from err

    async def pair(self) -> dict:
        """Send Pair Request, return the Pair Response."""
        self.tid = str(uuid.uuid4())
        self.controllernonce = str(uuid.uuid4())
        await self._send({
            "command_name": "Pair Request",
            "tid": self.tid,
            "name": "Unfolded Circle",
            "manufacturer": "Comcast",
            "model": "IPRemote",
            "controllernonce": self.controllernonce,
        })
        resp = await self._recv()
        if not resp.get("status"):
            raise SkyRemoteAuthError(f"Pair failed: {resp}")
        self.device_name = resp.get("name", "Sky Box")
        return resp

    async def bind(self, pairingcode: str, stbnonce: str) -> dict:
        """Compute the auth token and send Bind Request."""
        self.authtoken = compute_authtoken(
            cert_fingerprint=_CERT_FINGERPRINT,
            pairingcode=pairingcode,
            controllernonce=self.controllernonce,
            stbnonce=stbnonce,
        )
        await self._send({
            "command_name": "Bind Request",
            "tid": self.tid,
            "authtoken": self.authtoken,
        })
        resp = await self._recv()
        if not resp.get("status"):
            raise SkyRemoteAuthError(f"Bind failed: {resp}")
        self.bind_id = resp.get("bind_id")
        _LOG.info("Bound to %s (bind_id=%s)", self.device_name, self.bind_id)
        return resp

    async def connect_and_bind(self) -> None:
        """Full sequence: connect -> pair -> bind."""
        await self.connect()
        pair_resp = await self.pair()
        await self.bind(pair_resp.get("pairingcode", ""), pair_resp.get("stbnonce", ""))

    async def send_key(self, key: str) -> dict:
        """Send a single key command. Returns the STB response."""
        if not self.connected:
            raise SkyRemoteConnectionError("Not connected/bound")
        await self._send({
            "command_name": "Key Command Request",
            "tid": self.tid,
            "authtoken": self.authtoken,
            "bind_id": self.bind_id,
            "cmd": "keyatomic",
            "key": key,
        })
        return await self._recv(timeout=5.0)
