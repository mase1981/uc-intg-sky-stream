"""mDNS discovery for Sky Stream / Sky Glass boxes (_rdk-rics._tcp.local.)."""

import asyncio
import logging
import socket

from uc_intg_sky_stream.const import DEFAULT_PORT, MDNS_SERVICE_TYPE

_LOG = logging.getLogger(__name__)


def _scan_sync(timeout: float) -> list[dict[str, str]]:
    """Blocking zeroconf browse. Returns discovered devices."""
    try:
        import time

        from zeroconf import ServiceBrowser, Zeroconf
    except ImportError:
        _LOG.warning("zeroconf not available - discovery disabled")
        return []

    devices: dict[str, dict[str, str]] = {}

    class _Listener:
        def remove_service(self, zc, type_, name):  # noqa: D401
            pass

        def update_service(self, zc, type_, name):
            pass

        def add_service(self, zc, type_, name):
            try:
                info = zc.get_service_info(type_, name)
            except Exception:  # pylint: disable=broad-exception-caught
                info = None
            if not info or not info.addresses:
                return
            props: dict[str, str] = {}
            for key, val in (info.properties or {}).items():
                dkey = key.decode("utf-8", "replace") if isinstance(key, bytes) else str(key)
                dval = val.decode("utf-8", "replace") if isinstance(val, bytes) else str(val)
                props[dkey] = dval
            host = socket.inet_ntoa(info.addresses[0])
            devices[host] = {
                "name": info.name.split(".")[0] if info.name else "Sky Box",
                "host": host,
                "port": str(info.port or DEFAULT_PORT),
                "mac": props.get("wol_mac") or props.get("wowl_mac") or "",
            }

    zc = Zeroconf()
    try:
        ServiceBrowser(zc, MDNS_SERVICE_TYPE, _Listener())
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            time.sleep(0.2)
    finally:
        zc.close()
    return list(devices.values())


async def discover(timeout: float = 5.0) -> list[dict[str, str]]:
    """Discover Sky boxes on the LAN via mDNS (runs the blocking scan in a thread)."""
    try:
        return await asyncio.to_thread(_scan_sync, timeout)
    except Exception as err:  # pylint: disable=broad-exception-caught
        _LOG.debug("Sky discovery failed: %s", err)
        return []
