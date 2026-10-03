# Sky Stream Integration for Unfolded Circle Remote 2/3

Control your **Sky Stream** and **Sky Glass** boxes directly from your Unfolded Circle Remote 2 or Remote 3. Full navigation, playback, colour buttons, channel and volume, digit entry, and power - controlled **entirely locally** over your network with **no Sky account, cloud service, or subscription login** required.

> **Which integration do I need?** This is for **Sky Stream** pucks and **Sky Glass** TVs (the streaming boxes that run the Sky OS / Entertainment OS). For older **Sky Q** satellite boxes, use the separate [Sky Q integration](https://github.com/mase1981/uc-intg-skyq). The quick test: if your box **streams over the internet** (no satellite dish) → this integration; if it uses a **dish / Sky Q remote** → the other one.

![Sky](https://img.shields.io/badge/Sky-Stream%20%26%20Glass-0072C9)
[![GitHub Release](https://img.shields.io/github/v/release/mase1981/uc-intg-sky-stream?style=flat-square)](https://github.com/mase1981/uc-intg-sky-stream/releases)
![License](https://img.shields.io/badge/license-MPL--2.0-blue?style=flat-square)
[![GitHub issues](https://img.shields.io/github/issues/mase1981/uc-intg-sky-stream?style=flat-square)](https://github.com/mase1981/uc-intg-sky-stream/issues)
[![Community Forum](https://img.shields.io/badge/community-forum-blue?style=flat-square)](https://unfolded.community/)
[![Discord](https://badgen.net/discord/online-members/zGVYf58)](https://discord.gg/zGVYf58)
![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/mase1981/uc-intg-sky-stream/total?style=flat-square)
[![Buy Me A Coffee](https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=flat-square)](https://buymeacoffee.com/meirmiyara)
[![PayPal](https://img.shields.io/badge/PayPal-donate-blue.svg?style=flat-square)](https://paypal.me/mmiyara)
[![Github Sponsors](https://img.shields.io/badge/GitHub%20Sponsors-30363D?&logo=GitHub-Sponsors&logoColor=EA4AAA&style=flat-square)](https://github.com/sponsors/mase1981)

## Supported Devices

Sky streaming boxes on the local network, including: **Sky Stream** puck and **Sky Glass** TV (UK and international variants running Sky OS / Comcast Entertainment OS). Older **Sky Q** satellite boxes are **not** supported here - see the note above.

## Features

- **📺 Full remote entity** - navigation (up/down/left/right/OK/back), Home, Menu, Info, Options, Search, Settings, and Sky+ as simple commands for Activities, with physical button mapping and ready-made button pages.
- **🎬 Playback controls** - play/pause, rewind, fast-forward, and record.
- **🔴 Colour buttons** - Red, Green, Yellow, Blue interactive buttons.
- **🔢 Channel & digits** - channel up/down and digits 0-9 for direct channel entry.
- **🔊 Media player** - power on/off, volume up/down, mute, and transport as a set-top-box media player.
- **⚡ Wake-on-LAN** - power the box on from standby when it was discovered on the network.
- **🔒 Fully local** - direct LAN control, no Sky account and no cloud in the loop.
- **Multi-device** - add each Sky box on your network.

---
## ❤️ Support Development ❤️

If you find this integration useful, consider supporting development:

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-GitHub-pink?style=for-the-badge&logo=github)](https://github.com/sponsors/mase1981)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/meirmiyara)
[![PayPal](https://img.shields.io/badge/PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/mmiyara)

Your support helps maintain this integration. Thank you! ❤️
---

## How It Works

Sky Stream and Sky Glass boxes expose the same local remote-control protocol used by the official Sky Remote app. This integration speaks that protocol directly:

- **No account, no cloud** - control runs entirely over your local network. Nothing is sent to Sky's servers.
- **Automatic pairing** - the box accepts the pairing automatically; **no PIN is shown on the TV** and nothing needs to be entered.
- **State follows the box** - the integration reports the box as **On** when it is awake and **Off** when it is in standby (based on network reachability).

> This integration uses a community-documented local protocol reverse-engineered by the [sky_stream_remote](https://github.com/jatatech/sky_stream_remote) project. It is not affiliated with or endorsed by Sky, and Sky could change the protocol at any time. Because the protocol is command-only, live now-playing information (programme title, artwork) is not available.

## Requirements

- A Sky Stream puck or Sky Glass TV on the same network as your Remote.
- The box powered on (not in standby) during setup.
- Unfolded Circle Remote 2 / 3 with firmware supporting custom integrations.

## Installation

### Option 1: Remote Web Interface (Recommended)

1. Download the latest `uc-intg-sky-stream-<version>.tar.gz` from the [**Releases**](https://github.com/mase1981/uc-intg-sky-stream/releases) page.
2. Open your Remote's web interface (`http://your-remote-ip`).
3. Go to **Settings -> Integrations -> Add Integration -> Install Custom** and upload the `.tar.gz`.

### Option 2: Docker (Advanced Users)

**Image**: `ghcr.io/mase1981/uc-intg-sky-stream:latest`

**Docker Compose:**
```yaml
services:
  uc-intg-sky-stream:
    image: ghcr.io/mase1981/uc-intg-sky-stream:latest
    container_name: uc-intg-sky-stream
    network_mode: host
    volumes:
      - ./config:/config
    environment:
      - UC_CONFIG_HOME=/config
      - UC_INTEGRATION_HTTP_PORT=9090
      - UC_INTEGRATION_INTERFACE=0.0.0.0
      - PYTHONPATH=/app
    restart: unless-stopped
```

**Docker Run:**
```bash
docker run -d --name uc-intg-sky-stream --restart unless-stopped --network host -v $(pwd)/config:/config -e UC_CONFIG_HOME=/config -e UC_INTEGRATION_INTERFACE=0.0.0.0 -e UC_INTEGRATION_HTTP_PORT=9090 -e PYTHONPATH=/app ghcr.io/mase1981/uc-intg-sky-stream:latest
```

## Configuration

1. Make sure your Sky box is **powered on** (not in standby) and on the same network as the Remote.
2. Start setup. Your boxes are **discovered automatically**; if you have more than one, pick the box to add. If discovery finds nothing, **enter the box's IP address** manually.
   - **MAC Address (optional)**: only needed to power the box on from standby when it was added by IP and the integration could not find its MAC on the network. Format `AA:BB:CC:DD:EE:FF`.
   - If something goes wrong, setup shows what happened on the same screen so you can correct it.
3. Repeat setup to add additional Sky boxes.

For each device the integration creates:

| Entity | Purpose |
|--------|---------|
| **Remote** (`<name> Remote`) | Full button surface (navigation, playback, colour, channel, volume, digits, power) as simple commands for Activities, with button pages. Send Command supports repeat and delay, command sequences (list or comma separated), and the box's own key names (e.g. `ArrowUp`, `Digit5`). |
| **Media player** (`<name>`) | Power on/off, volume, mute, play/pause, fast-forward/rewind, and channel next/previous. |

> **Note:** Wake-on-LAN needs the box's MAC address. It is captured automatically when the box is discovered; for a box added by IP, setup looks it up on the network, or you can enter it in the optional MAC Address field.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| "No Sky box answered on the network" | Ensure the box is powered on and on the same network/subnet as the Remote, then enter the IP manually. |
| "No answer from <IP> on port 8091" | Wrong IP, box in standby, or the Remote and box are on different networks. From a PC on the same network, `Test-NetConnection <IP> -Port 8091` (Windows) shows whether the box accepts the connection. |
| "Refused the Sky remote control connection" | The device at that IP is not accepting Sky remote control; check the IP is the Sky box. |
| Pairing keeps failing | Repeated failed pairings can temporarily lock the box out - reboot the Sky box and try again. |
| Commands do nothing | The box must be awake to accept commands; power it on first. |
| Cannot power on from standby | Wake-on-LAN needs the box's MAC address - re-run setup and enter it in the optional MAC Address field. |
| No programme title or artwork | The Sky local protocol is command-only and does not report now-playing information; this is a protocol limitation, not a bug. |

## Credits

- **Developer**: Meir Miyara
- **Sky local protocol**: [jatatech/sky_stream_remote](https://github.com/jatatech/sky_stream_remote) (community reverse-engineering).
- **Unfolded Circle**: Remote 2/3 integration framework ([ucapi](https://github.com/unfoldedcircle/integration-python-library) / [ucapi-framework](https://github.com/JackJPowell/ucapi-framework)).

## License

Mozilla Public License 2.0 (MPL-2.0) - see the LICENSE file.

## Support & Community

- **GitHub Issues**: [Report bugs and request features](https://github.com/mase1981/uc-intg-sky-stream/issues)
- **UC Community Forum**: [General discussion and support](https://unfolded.community/)
- **Developer**: [Meir Miyara](https://www.linkedin.com/in/meirmiyara)

---

**Made with ❤️ for the Unfolded Circle Community**

**Thank You**: Meir Miyara
