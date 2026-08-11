"""Setup flow: discover Sky boxes via mDNS, or enter an IP manually.

Setup connects once to pair + bind (proving the box is reachable and controllable)
and to read the box's friendly name. Repeated *failed* binds can lock out the STB,
so the setup only attempts a single bind per submission.
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
    is_box_reachable,
)
from uc_intg_sky_stream.config import SkyStreamConfig
from uc_intg_sky_stream.const import DEFAULT_PORT

_LOG = logging.getLogger(__name__)

_MANUAL = "manual"


class SkyStreamSetupFlow(BaseSetupFlow[SkyStreamConfig]):
    """Discover Sky Stream boxes and add the chosen one."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._devices: list[dict[str, str]] = []

    def get_manual_entry_form(self) -> RequestUserInput:
        return RequestUserInput(
            {"en": "Sky Stream Setup"},
            [
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
                    "field": {"text": {"value": ""}},
                },
            ],
        )

    async def query_device(self, input_values: dict[str, Any]) -> SkyStreamConfig | RequestUserInput:
        host = input_values.get("host", "").strip()

        if host:
            return await self._build_from_host(host, DEFAULT_PORT, "")

        _LOG.info("Discovering Sky boxes on the network...")
        self._devices = await discovery.discover(timeout=6.0)
        _LOG.info("Discovered %d Sky box(es)", len(self._devices))

        if not self._devices:
            raise ValueError(
                "No Sky boxes were found on the network. Make sure the box is powered on "
                "and on the same network as the Remote, then try again and enter the IP "
                "address manually."
            )

        if len(self._devices) == 1:
            dev = self._devices[0]
            return await self._build_from_host(dev["host"], int(dev.get("port", DEFAULT_PORT)), dev.get("mac", ""))

        items = [{"id": d["host"], "label": {"en": f"{d['name']} ({d['host']})"}} for d in self._devices]
        return RequestUserInput(
            {"en": "Select Sky Box"},
            [{
                "id": "device",
                "label": {"en": "Device"},
                "field": {"dropdown": {"value": items[0]["id"], "items": items}},
            }],
        )

    async def handle_additional_configuration_response(self, msg: Any) -> SkyStreamConfig | None:
        host = msg.input_values.get("device", "")
        dev = next((d for d in self._devices if d["host"] == host), None)
        if not dev:
            raise ValueError("Selected device not found")
        self._pending_device_config = await self._build_from_host(
            dev["host"], int(dev.get("port", DEFAULT_PORT)), dev.get("mac", "")
        )
        return None

    async def _build_from_host(self, host: str, port: int, mac: str) -> SkyStreamConfig:
        if not await is_box_reachable(host, port):
            raise ValueError(
                f"Sky box at {host} is not reachable. Check the IP address and make sure "
                "the box is powered on (not in standby)."
            )

        client = SkyRemoteClient(host, port)
        name = "Sky Box"
        try:
            await client.connect_and_bind()
            name = client.device_name or name
        except SkyRemoteError as err:
            _LOG.error("Sky pairing failed for %s: %s", host, err)
            raise ValueError(
                f"Could not pair with the Sky box at {host}: {err}. If pairing keeps failing, "
                "reboot the box and try again."
            ) from err
        finally:
            await client.disconnect()

        identifier = f"sky_{re.sub(r'[^A-Za-z0-9]', '_', host)}"
        return SkyStreamConfig(identifier=identifier, name=name, host=host, port=port, mac=mac)
