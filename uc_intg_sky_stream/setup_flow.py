"""Setup flow: discover Sky boxes via mDNS, or enter an IP manually.

Setup connects once to pair + bind (proving the box is reachable and controllable)
and to read the box's friendly name. Repeated *failed* binds can lock out the STB,
so the setup only attempts a single bind per submission.

Every problem is shown on the form with what to do next, and the form keeps what
the user typed, instead of ending the setup with a bare "not found".
"""

import logging
import re
from typing import Any

from ucapi import RequestUserInput
from ucapi_framework import BaseSetupFlow

from uc_intg_sky_stream import discovery
from uc_intg_sky_stream.client import (
    SkyRemoteClient,
    SkyRemoteError,
    probe_box,
)
from uc_intg_sky_stream.config import SkyStreamConfig
from uc_intg_sky_stream.const import DEFAULT_PORT

_LOG = logging.getLogger(__name__)

_DISCOVERY_TIMEOUT = 6.0
_MAC_LOOKUP_TIMEOUT = 3.0
_PROBE_TIMEOUT = 3.0
_MAC = re.compile(r"^[0-9a-f]{12}$")


class SetupProblem(Exception):
    """A setup problem to show on the form."""


class SkyStreamSetupFlow(BaseSetupFlow[SkyStreamConfig]):
    """Discover Sky Stream boxes and add the chosen one."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._devices: list[dict[str, str]] = []

    def get_manual_entry_form(self, error: str = "", values: dict | None = None) -> RequestUserInput:
        values = values or {}
        fields = []
        if error:
            fields.append({
                "id": "error",
                "label": {"en": "Problem"},
                "field": {"label": {"value": {"en": error}}},
            })
        fields += [
            {
                "id": "info",
                "label": {"en": "Sky Stream / Sky Glass"},
                "field": {"label": {"value": {"en": (
                    "Your Sky boxes are discovered automatically on the network. "
                    "Leave the IP address blank to auto-discover, or enter it manually "
                    "if discovery does not find your box. The box must be powered on "
                    "(not in standby) during setup."
                )}}},
            },
            {
                "id": "host",
                "label": {"en": "IP Address (optional)"},
                "field": {"text": {"value": values.get("host", "")}},
            },
            {
                "id": "mac",
                "label": {"en": "MAC Address (optional, to power on from standby)"},
                "field": {"text": {"value": values.get("mac", "")}},
            },
        ]
        return RequestUserInput({"en": "Sky Stream Setup"}, fields)

    async def query_device(self, input_values: dict[str, Any]) -> SkyStreamConfig | RequestUserInput:
        # The box picker's answer comes back through here as well.
        if input_values.get("device"):
            return await self._from_picker(input_values["device"])

        host, port = _parse_host(input_values.get("host"))
        mac_text = str(input_values.get("mac") or "").strip()
        values = {"host": str(input_values.get("host") or "").strip(), "mac": mac_text}
        mac = _parse_mac(mac_text)
        if mac_text and not mac:
            return self.get_manual_entry_form(
                "The MAC address looks wrong. Use the format AA:BB:CC:DD:EE:FF, or leave it empty.", values
            )

        if host:
            if not mac:
                mac = await self._lookup_mac(host)
            try:
                return await self._build_from_host(host, port, mac)
            except SetupProblem as err:
                return self.get_manual_entry_form(str(err), values)

        _LOG.info("Discovering Sky boxes on the network...")
        self._devices = await discovery.discover(timeout=_DISCOVERY_TIMEOUT)
        _LOG.info("Discovered %d Sky box(es)", len(self._devices))

        if not self._devices:
            return self.get_manual_entry_form(
                "No Sky box answered on the network. Make sure the box is powered on (not in standby) "
                "and on the same network as the Remote, then enter its IP address.",
                values,
            )

        if len(self._devices) == 1:
            dev = self._devices[0]
            try:
                return await self._build_from_host(
                    dev["host"], int(dev.get("port") or DEFAULT_PORT), dev.get("mac") or mac
                )
            except SetupProblem as err:
                return self.get_manual_entry_form(str(err), {**values, "host": dev["host"]})

        items = [{"id": d["host"], "label": {"en": f"{d['name']} ({d['host']})"}} for d in self._devices]
        return RequestUserInput(
            {"en": "Select Sky Box"},
            [{
                "id": "device",
                "label": {"en": "Device"},
                "field": {"dropdown": {"value": items[0]["id"], "items": items}},
            }],
        )

    async def handle_additional_configuration_response(self, msg: Any) -> SkyStreamConfig | RequestUserInput | None:
        # Kept for safety; the picker answer normally arrives in query_device().
        result = await self._from_picker(msg.input_values.get("device", ""))
        if isinstance(result, SkyStreamConfig):
            self._pending_device_config = result
            return None
        self._pending_device_config = None
        return result

    async def _from_picker(self, host: str) -> SkyStreamConfig | RequestUserInput:
        dev = next((d for d in self._devices if d["host"] == host), None)
        if not dev:
            return self.get_manual_entry_form("That box is no longer listed. Search again or enter its IP address.")
        try:
            return await self._build_from_host(dev["host"], int(dev.get("port") or DEFAULT_PORT), dev.get("mac", ""))
        except SetupProblem as err:
            return self.get_manual_entry_form(str(err), {"host": dev["host"]})

    async def _lookup_mac(self, host: str) -> str:
        """Find the Wake-on-LAN MAC for a box entered by IP (it announces it over mDNS)."""
        try:
            devices = await discovery.discover(timeout=_MAC_LOOKUP_TIMEOUT)
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOG.debug("MAC lookup failed: %s", err)
            return ""
        mac = next((d.get("mac", "") for d in devices if d.get("host") == host), "")
        _LOG.info("Wake-on-LAN MAC for %s: %s", host, mac or "not found")
        return mac

    async def _build_from_host(self, host: str, port: int, mac: str) -> SkyStreamConfig:
        result = await probe_box(host, port, timeout=_PROBE_TIMEOUT)
        if result == "refused":
            raise SetupProblem(
                f"{host} answered but refused the Sky remote control connection (port {port}). "
                "Check that this is the Sky box's IP address. Some Sky boxes or regions may not "
                "offer local remote control."
            )
        if result != "ok":
            raise SetupProblem(
                f"No answer from {host} on port {port}. Check the IP address, make sure the box is "
                "powered on (not in standby), and that the Remote and the box are on the same network."
            )

        client = SkyRemoteClient(host, port)
        name = "Sky Box"
        try:
            await client.connect_and_bind()
            name = client.device_name or name
        except SkyRemoteError as err:
            _LOG.error("Sky pairing failed for %s: %s", host, err)
            raise SetupProblem(
                f"Could not pair with the Sky box at {host}: {err}. If pairing keeps failing, "
                "reboot the box and try again."
            ) from err
        finally:
            await client.disconnect()

        identifier = f"sky_{re.sub(r'[^A-Za-z0-9]', '_', host)}"
        return SkyStreamConfig(identifier=identifier, name=name, host=host, port=port, mac=mac)


def _parse_host(value: Any) -> tuple[str, int]:
    """Accept "192.168.1.20", "192.168.1.20:8091", "http://192.168.1.20/" and stray spaces."""
    text = re.sub(r"\s+", "", str(value or ""))
    text = re.sub(r"^[a-zA-Z]+://", "", text).split("/")[0]
    port = DEFAULT_PORT
    if text.count(":") == 1:
        text, _, port_text = text.partition(":")
        if port_text.isdigit():
            port = int(port_text)
    return text, port


def _parse_mac(value: str) -> str:
    """Normalise a MAC to AA:BB:CC:DD:EE:FF, or "" if it is not one."""
    digits = re.sub(r"[^0-9a-fA-F]", "", value or "").lower()
    if not _MAC.match(digits) or re.sub(r"[\s:.\-]", "", value or "").lower() != digits:
        return ""
    return ":".join(digits[i:i + 2] for i in range(0, 12, 2)).upper()
