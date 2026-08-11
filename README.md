# Sky Stream — Unfolded Circle Integration

Control **Sky Stream** and **Sky Glass** boxes from your Unfolded Circle Remote Two/3, entirely over your local network. No Sky account, cloud service, or subscription login is required — control is local and instant.

This integration speaks the same LAN protocol the official Sky Remote app uses (mTLS + WebSocket on port `8091`), so it drives the box directly with no middleman.

![Sky](https://img.shields.io/badge/Sky-Stream%20%26%20Glass-0072C9)
![Version](https://img.shields.io/github/v/release/mase1981/uc-intg-sky-stream)
![License](https://img.shields.io/badge/license-MPL--2.0-green)

---

## Features

Two entities are created for each Sky box:

### Remote
The full Sky button surface, ready for activities and macros:

- **Navigation:** Up, Down, Left, Right, OK, Back, Dismiss, Home
- **Menus:** Menu, Info, Options, Search, Settings, Sky+
- **Playback:** Play/Pause, Rewind, Fast-Forward, Record
- **Channel & Volume:** Channel Up/Down, Volume Up/Down, Mute
- **Colour buttons:** Red, Green, Yellow, Blue
- **Digits:** 0–9 (enter channel numbers directly)
- **Power:** discrete `POWER_ON` / `POWER_OFF` (for activities) and `POWER` toggle

Physical Remote buttons and two on-screen UI pages are pre-mapped out of the box.

### Media Player
A simple receiver-style media player with Power on/off/toggle, Volume Up/Down, Mute, Play/Pause, and Channel next/previous.

### Wake-on-LAN
When a box is discovered via mDNS, its MAC address is stored so the integration can wake it from standby with a Wake-on-LAN magic packet when you power it on.

---

## Installation

### Option 1: Upload to the Remote (recommended)

1. Download the latest `uc-intg-sky-stream-*-aarch64.tar.gz` from the [Releases](https://github.com/mase1981/uc-intg-sky-stream/releases) page.
2. In the Remote web configurator, go to **Integrations → Add New → Install Custom** and upload the `.tar.gz`.
3. Start setup (see below).

### Option 2: Docker

```bash
docker run -d --name uc-intg-sky-stream --network host \
  -v $(pwd)/config:/config \
  -e UC_INTEGRATION_HTTP_PORT=9090 \
  ghcr.io/mase1981/uc-intg-sky-stream:latest
```

Then add it to the Remote as an external integration pointing at the host's IP and port `9090`.

---

## Setup

1. Make sure your Sky box is **powered on** (not in standby) and on the same network as the Remote.
2. Start the integration setup.
3. Your boxes are **discovered automatically**. If you have more than one, pick it from the list. If discovery finds nothing, enter the box's **IP address** manually.
4. The integration pairs and binds to the box (no PIN is shown on the TV — pairing is automatic) and reads its friendly name.
5. The **Remote** and **Media Player** entities are added and ready to use.

> **Note:** Repeated *failed* pairing attempts can temporarily lock the box out of pairing. If pairing keeps failing, reboot the Sky box and try again.

---

## How It Works

| Layer | Detail |
|-------|--------|
| Discovery | mDNS `_rdk-rics._tcp.local.` |
| Transport | TLS 1.3 (mTLS) on TCP `8091` |
| Session | WebSocket `/iptarget` → Pair → Bind → `keyatomic` key commands |
| State | Reachability probe (ON when awake, OFF in standby) |
| Wake | Wake-on-LAN magic packet to the box's MAC |

The mTLS client identity is the shared identity from the Sky Remote app and is embedded in the integration — nothing needs to be configured.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Box not discovered | Ensure it is powered on and on the same subnet; enter the IP manually |
| Pairing fails repeatedly | Reboot the Sky box to clear a pairing lockout |
| Can't power on from standby | Wake-on-LAN needs the box's MAC — this is only captured via mDNS discovery, not manual IP entry |
| Commands do nothing when box is off | Power the box on first; it must be awake to accept commands |

---

## Acknowledgements

The Sky LAN control protocol was reverse-engineered by the [jatatech/sky_stream_remote](https://github.com/jatatech/sky_stream_remote) project. This integration reimplements that verified protocol for the Unfolded Circle platform.

---

## Support

- **Issues:** [GitHub Issues](https://github.com/mase1981/uc-intg-sky-stream/issues)
- **Author:** Meir Miyara

If you find this integration useful, consider supporting development:

- [Buy Me a Coffee](https://www.buymeacoffee.com/meirmiyara)
- [PayPal](https://paypal.me/mmiyara)

---

*Sky, Sky Stream, and Sky Glass are trademarks of Sky UK Limited. This project is not affiliated with, endorsed by, or sponsored by Sky.*
