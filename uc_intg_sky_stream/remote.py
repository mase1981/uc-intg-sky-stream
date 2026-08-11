"""Sky Stream remote entity - full button surface for activities."""

import logging
from typing import Any

from ucapi import StatusCodes, remote
from ucapi.ui import (
    Buttons,
    Size,
    UiPage,
    create_btn_mapping,
    create_ui_icon,
    create_ui_text,
)
from ucapi_framework import RemoteEntity

from uc_intg_sky_stream.config import SkyStreamConfig
from uc_intg_sky_stream.const import (
    KEY_ARROW_DOWN,
    KEY_ARROW_LEFT,
    KEY_ARROW_RIGHT,
    KEY_ARROW_UP,
    KEY_BACK,
    KEY_BLUE,
    KEY_CHANNEL_DOWN,
    KEY_CHANNEL_UP,
    KEY_DISMISS,
    KEY_ENTER,
    KEY_FAST_FORWARD,
    KEY_GREEN,
    KEY_HOME,
    KEY_INFO,
    KEY_MENU,
    KEY_MUTE,
    KEY_OPTION,
    KEY_PLAY_PAUSE,
    KEY_PLUS,
    KEY_RECORD,
    KEY_RED,
    KEY_REWIND,
    KEY_SEARCH,
    KEY_SETTINGS,
    KEY_SOURCE,
    KEY_VOLUME_DOWN,
    KEY_VOLUME_UP,
    KEY_YELLOW,
    STATE_ON,
)
from uc_intg_sky_stream.device import SkyStreamDevice

_LOG = logging.getLogger(__name__)

# Simple command name -> STB key. Names are the UC-facing command identifiers.
COMMAND_MAP: dict[str, str] = {
    "UP": KEY_ARROW_UP,
    "DOWN": KEY_ARROW_DOWN,
    "LEFT": KEY_ARROW_LEFT,
    "RIGHT": KEY_ARROW_RIGHT,
    "OK": KEY_ENTER,
    "BACK": KEY_BACK,
    "DISMISS": KEY_DISMISS,
    "HOME": KEY_HOME,
    "MENU": KEY_MENU,
    "INFO": KEY_INFO,
    "OPTION": KEY_OPTION,
    "SEARCH": KEY_SEARCH,
    "SETTINGS": KEY_SETTINGS,
    "CHANNEL_UP": KEY_CHANNEL_UP,
    "CHANNEL_DOWN": KEY_CHANNEL_DOWN,
    "VOLUME_UP": KEY_VOLUME_UP,
    "VOLUME_DOWN": KEY_VOLUME_DOWN,
    "MUTE": KEY_MUTE,
    "PLAY_PAUSE": KEY_PLAY_PAUSE,
    "RECORD": KEY_RECORD,
    "REWIND": KEY_REWIND,
    "FAST_FORWARD": KEY_FAST_FORWARD,
    "SOURCE": KEY_SOURCE,
    "SKY_PLUS": KEY_PLUS,
    "RED": KEY_RED,
    "GREEN": KEY_GREEN,
    "YELLOW": KEY_YELLOW,
    "BLUE": KEY_BLUE,
    "DIGIT_0": "Digit0",
    "DIGIT_1": "Digit1",
    "DIGIT_2": "Digit2",
    "DIGIT_3": "Digit3",
    "DIGIT_4": "Digit4",
    "DIGIT_5": "Digit5",
    "DIGIT_6": "Digit6",
    "DIGIT_7": "Digit7",
    "DIGIT_8": "Digit8",
    "DIGIT_9": "Digit9",
}

SIMPLE_COMMANDS = ["POWER", "POWER_ON", "POWER_OFF"] + list(COMMAND_MAP.keys())


class SkyStreamRemote(RemoteEntity):
    """Exposes the full Sky button surface as simple commands for activities."""

    def __init__(self, device_config: SkyStreamConfig, device: SkyStreamDevice) -> None:
        self._device = device
        entity_id = f"remote.{device_config.identifier}"
        super().__init__(
            entity_id,
            f"{device_config.name} Remote",
            [remote.Features.ON_OFF, remote.Features.TOGGLE, remote.Features.SEND_CMD],
            {remote.Attributes.STATE: remote.States.UNKNOWN},
            simple_commands=SIMPLE_COMMANDS,
            button_mapping=[
                create_btn_mapping(Buttons.DPAD_UP, short="UP"),
                create_btn_mapping(Buttons.DPAD_DOWN, short="DOWN"),
                create_btn_mapping(Buttons.DPAD_LEFT, short="LEFT"),
                create_btn_mapping(Buttons.DPAD_RIGHT, short="RIGHT"),
                create_btn_mapping(Buttons.DPAD_MIDDLE, short="OK"),
                create_btn_mapping(Buttons.HOME, short="HOME"),
                create_btn_mapping(Buttons.BACK, short="BACK"),
                create_btn_mapping(Buttons.MENU, short="MENU"),
                create_btn_mapping(Buttons.VOLUME_UP, short="VOLUME_UP"),
                create_btn_mapping(Buttons.VOLUME_DOWN, short="VOLUME_DOWN"),
                create_btn_mapping(Buttons.MUTE, short="MUTE"),
                create_btn_mapping(Buttons.CHANNEL_UP, short="CHANNEL_UP"),
                create_btn_mapping(Buttons.CHANNEL_DOWN, short="CHANNEL_DOWN"),
                create_btn_mapping(Buttons.PREV, short="REWIND"),
                create_btn_mapping(Buttons.PLAY, short="PLAY_PAUSE"),
                create_btn_mapping(Buttons.NEXT, short="FAST_FORWARD"),
                create_btn_mapping(Buttons.POWER, short="POWER"),
            ],
            ui_pages=[
                UiPage("nav", "Sky", grid=Size(4, 6), items=[
                    create_ui_icon("uc:power-on", 0, 0, cmd="POWER_ON"),
                    create_ui_text("Home", 1, 0, cmd="HOME"),
                    create_ui_text("Menu", 2, 0, cmd="MENU"),
                    create_ui_icon("uc:power-off", 3, 0, cmd="POWER_OFF"),
                    create_ui_text("Up", 1, 2, cmd="UP"),
                    create_ui_text("Left", 0, 3, cmd="LEFT"),
                    create_ui_text("OK", 1, 3, cmd="OK"),
                    create_ui_text("Right", 2, 3, cmd="RIGHT"),
                    create_ui_text("Down", 1, 4, cmd="DOWN"),
                    create_ui_text("Back", 3, 3, cmd="BACK"),
                    create_ui_text("Info", 0, 1, cmd="INFO"),
                    create_ui_text("Search", 2, 1, cmd="SEARCH"),
                    create_ui_text("Options", 3, 1, cmd="OPTION"),
                    create_ui_text("Sky+", 0, 5, cmd="SKY_PLUS"),
                    create_ui_text("Settings", 3, 5, cmd="SETTINGS"),
                ]),
                UiPage("media", "Playback", grid=Size(4, 6), items=[
                    create_ui_icon("uc:bw", 0, 0, cmd="REWIND"),
                    create_ui_icon("uc:play", 1, 0, cmd="PLAY_PAUSE"),
                    create_ui_icon("uc:ff", 2, 0, cmd="FAST_FORWARD"),
                    create_ui_text("Rec", 3, 0, cmd="RECORD"),
                    create_ui_icon("uc:volume-up", 3, 2, cmd="VOLUME_UP"),
                    create_ui_icon("uc:volume-down", 3, 3, cmd="VOLUME_DOWN"),
                    create_ui_icon("uc:mute", 3, 4, cmd="MUTE"),
                    create_ui_text("CH +", 0, 2, cmd="CHANNEL_UP"),
                    create_ui_text("CH -", 0, 3, cmd="CHANNEL_DOWN"),
                    create_ui_text("Red", 0, 5, cmd="RED"),
                    create_ui_text("Green", 1, 5, cmd="GREEN"),
                    create_ui_text("Yellow", 2, 5, cmd="YELLOW"),
                    create_ui_text("Blue", 3, 5, cmd="BLUE"),
                ]),
            ],
            cmd_handler=self._handle_command,
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        state = remote.States.ON if self._device.state == STATE_ON else remote.States.OFF
        self.update({remote.Attributes.STATE: state})

    async def _handle_command(self, entity: Any, cmd_id: str, params: dict | None = None, *_a: Any) -> StatusCodes:
        try:
            if cmd_id == remote.Commands.ON:
                await self._device.power_on()
                return StatusCodes.OK
            if cmd_id == remote.Commands.OFF:
                await self._device.power_off()
                return StatusCodes.OK
            if cmd_id == remote.Commands.TOGGLE:
                await self._device.power_toggle()
                return StatusCodes.OK
            if cmd_id != remote.Commands.SEND_CMD:
                return StatusCodes.NOT_IMPLEMENTED
            return await self._run((params or {}).get("command", ""))
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOG.error("[%s] Remote command error (%s): %s", entity.id, cmd_id, err)
            return StatusCodes.SERVER_ERROR

    async def _run(self, command: str) -> StatusCodes:
        if command == "POWER":
            await self._device.power_toggle()
            return StatusCodes.OK
        if command == "POWER_ON":
            await self._device.power_on()
            return StatusCodes.OK
        if command == "POWER_OFF":
            await self._device.power_off()
            return StatusCodes.OK
        key = COMMAND_MAP.get(command)
        if key is None:
            return StatusCodes.NOT_IMPLEMENTED
        await self._device.send_key(key)
        return StatusCodes.OK


def create_remote(device_config: SkyStreamConfig, device: SkyStreamDevice) -> list[SkyStreamRemote]:
    return [SkyStreamRemote(device_config, device)]
