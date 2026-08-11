"""Integration driver for Sky Stream / Sky Glass."""

from ucapi_framework import BaseIntegrationDriver

from uc_intg_sky_stream.config import SkyStreamConfig
from uc_intg_sky_stream.device import SkyStreamDevice
from uc_intg_sky_stream.media_player import create_media_player
from uc_intg_sky_stream.remote import create_remote


class SkyStreamDriver(BaseIntegrationDriver[SkyStreamDevice, SkyStreamConfig]):
    """Builds a media_player and a remote per Sky box."""

    def __init__(self) -> None:
        super().__init__(
            device_class=SkyStreamDevice,
            entity_classes=[
                create_media_player,
                create_remote,
            ],
            driver_id="uc_intg_sky_stream",
        )
