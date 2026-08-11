"""Constants for the Sky Stream integration."""

DEFAULT_PORT = 8091
MDNS_SERVICE_TYPE = "_rdk-rics._tcp.local."

# Auth-token salt recovered from the Sky Remote app binary.
AUTH_SALT = b"biT43y"

STATE_ON = "ON"
STATE_OFF = "OFF"
STATE_UNAVAILABLE = "UNAVAILABLE"

# Verified working key names (tested against a real Sky STB).
# Source: the app's Dart enum plus firmware-accepted "box extra" keys.
KEY_ARROW_UP = "ArrowUp"
KEY_ARROW_DOWN = "ArrowDown"
KEY_ARROW_LEFT = "ArrowLeft"
KEY_ARROW_RIGHT = "ArrowRight"
KEY_ENTER = "Enter"
KEY_BACK = "Backspace"
KEY_DISMISS = "Dismiss"
KEY_HOME = "Home"
KEY_MENU = "AccessMenu"
KEY_INFO = "Info"
KEY_OPTION = "Option"
KEY_SEARCH = "Search"
KEY_SETTINGS = "Settings"
KEY_CHANNEL_UP = "ChannelUp"
KEY_CHANNEL_DOWN = "ChannelDown"
KEY_VOLUME_UP = "VolumeUp"
KEY_VOLUME_DOWN = "VolumeDown"
KEY_MUTE = "VolumeMute"
KEY_PLAY_PAUSE = "MediaPlay"
KEY_RECORD = "MediaRecord"
KEY_REWIND = "MediaRewind"
KEY_FAST_FORWARD = "MediaFastForward"
KEY_POWER = "Power"
KEY_SOURCE = "Source"
KEY_PLUS = "Plus"
KEY_RED = "Red"
KEY_GREEN = "Green"
KEY_YELLOW = "Yellow"
KEY_BLUE = "Blue"

# All keys the STB accepts (used to validate free-form send_cmd requests).
VERIFIED_KEYS: list[str] = [
    KEY_ARROW_UP, KEY_ARROW_DOWN, KEY_ARROW_LEFT, KEY_ARROW_RIGHT,
    KEY_ENTER, KEY_BACK, KEY_DISMISS, KEY_HOME,
    KEY_MENU, KEY_INFO, KEY_OPTION, KEY_SEARCH, KEY_SETTINGS,
    KEY_CHANNEL_UP, KEY_CHANNEL_DOWN,
    KEY_VOLUME_UP, KEY_VOLUME_DOWN, KEY_MUTE,
    KEY_PLAY_PAUSE, KEY_RECORD, KEY_REWIND, KEY_FAST_FORWARD,
    KEY_POWER, KEY_SOURCE, KEY_PLUS,
    KEY_RED, KEY_GREEN, KEY_YELLOW, KEY_BLUE,
    "Digit0", "Digit1", "Digit2", "Digit3", "Digit4",
    "Digit5", "Digit6", "Digit7", "Digit8", "Digit9",
]
