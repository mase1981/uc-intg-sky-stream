"""Configuration dataclass and manager for the Sky Stream integration."""

from dataclasses import dataclass

from ucapi_framework import BaseConfigManager

from uc_intg_sky_stream.const import DEFAULT_PORT


@dataclass
class SkyStreamConfig:
    """Configuration for a single Sky Stream / Sky Glass set-top box."""

    identifier: str = ""
    name: str = ""
    host: str = ""
    port: int = DEFAULT_PORT
    mac: str = ""  # Wake-on-LAN MAC from mDNS (empty for manual setup)


class SkyStreamConfigManager(BaseConfigManager[SkyStreamConfig]):
    """Config manager bound to :class:`SkyStreamConfig`."""
