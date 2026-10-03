"""Sky Stream media_player entity.

The RICS protocol is command-only (the box reports no playback state), so this
exposes transport/power/volume controls with state derived from reachability.
"""

import logging
from typing import Any

from ucapi import StatusCodes, media_player
from ucapi_framework import MediaPlayerEntity

from uc_intg_sky_stream.config import SkyStreamConfig
from uc_intg_sky_stream.const import STATE_ON
from uc_intg_sky_stream.device import SkyStreamDevice

_LOG = logging.getLogger(__name__)

FEATURES = [
    media_player.Features.ON_OFF,
    media_player.Features.TOGGLE,
    media_player.Features.VOLUME_UP_DOWN,
    media_player.Features.MUTE_TOGGLE,
    media_player.Features.PLAY_PAUSE,
    media_player.Features.FAST_FORWARD,
    media_player.Features.REWIND,
    media_player.Features.NEXT,
    media_player.Features.PREVIOUS,
]


class SkyStreamMediaPlayer(MediaPlayerEntity):
    """Media player for a Sky Stream / Sky Glass box."""

    def __init__(self, device_config: SkyStreamConfig, device: SkyStreamDevice) -> None:
        self._device = device
        entity_id = f"media_player.{device_config.identifier}"
        super().__init__(
            entity_id,
            device_config.name,
            FEATURES,
            {media_player.Attributes.STATE: media_player.States.UNKNOWN},
            device_class=media_player.DeviceClasses.SET_TOP_BOX,
            cmd_handler=self._handle_command,
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        state = media_player.States.ON if self._device.state == STATE_ON else media_player.States.OFF
        self.update({media_player.Attributes.STATE: state})

    async def _handle_command(self, entity: Any, cmd_id: str, params: dict | None = None, *_a: Any) -> StatusCodes:
        try:
            ok = True
            match cmd_id:
                # Power on/off answer OK as before: activities must not stop on a sleeping box.
                case media_player.Commands.ON:
                    await self._device.power_on()
                case media_player.Commands.OFF:
                    await self._device.power_off()
                case media_player.Commands.TOGGLE:
                    ok = await self._device.power_toggle()
                case media_player.Commands.PLAY_PAUSE:
                    ok = await self._device.play_pause()
                case media_player.Commands.FAST_FORWARD:
                    ok = await self._device.fast_forward()
                case media_player.Commands.REWIND:
                    ok = await self._device.rewind()
                case media_player.Commands.NEXT:
                    ok = await self._device.channel_up()
                case media_player.Commands.PREVIOUS:
                    ok = await self._device.channel_down()
                case media_player.Commands.VOLUME_UP:
                    ok = await self._device.volume_up()
                case media_player.Commands.VOLUME_DOWN:
                    ok = await self._device.volume_down()
                case media_player.Commands.MUTE_TOGGLE:
                    ok = await self._device.mute_toggle()
                case _:
                    return StatusCodes.NOT_IMPLEMENTED
            return StatusCodes.OK if ok else StatusCodes.SERVICE_UNAVAILABLE
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOG.error("[%s] Command error (%s): %s", entity.id, cmd_id, err)
            return StatusCodes.SERVER_ERROR


def create_media_player(device_config: SkyStreamConfig, device: SkyStreamDevice) -> list[SkyStreamMediaPlayer]:
    return [SkyStreamMediaPlayer(device_config, device)]
