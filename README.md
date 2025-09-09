# Home Assistant (HACS) custom integration

![GitHub release](https://img.shields.io/github/release/Loule95450/HACS-Nexecur.svg)
![GitHub repo size in bytes](https://img.shields.io/github/repo-size/Loule95450/HACS-Nexecur.svg)
![GitHub](https://img.shields.io/github/license/Loule95450/HACS-Nexecur.svg)

This is an unofficial API for the Nexecur system, forked from a deleted repository originally created by Baudev. This fork for HomeAssistant is maintained by Loule95450.

You can now install and use this API as a Home Assistant integration via HACS.

What you get:

- An Alarm control panel entity that shows the current state (armed/disarmed)
- Actions to arm and disarm the alarm from Home Assistant
- Camera entities for viewing RTSP streams from Nexecur cameras
- Automatic polling of the panel status and camera streams (every 30 seconds by default)
- Dynamic discovery of new cameras when they are added to your system

Installation (via HACS):

1. In HACS, add this repository as a Custom Repository (category: Integration).
2. Install the "Nexecur" integration.
3. Restart Home Assistant.
4. Go to Settings > Devices & Services > Add Integration > search for "Nexecur".
5. Enter your credentials:
   - id_site (wiring code)
   - password (PIN). Note: it is used to derive the secure hashes required by Nexecur.
   - deviceName (optional, used to register this instance with Nexecur; defaults to "Home Assistant").

Entity: after setup, you should see:
- An alarm entity like `alarm_control_panel.nexecur_alarm` to arm/disarm the system
- Camera entities like `camera.nexecur_camera_{site_id}_{serial}` for each discovered camera with streaming capability

Camera Features:
- RTSP streams are automatically refreshed every 30 seconds to maintain connection
- New cameras are automatically discovered when added to your Nexecur system
- Camera entities show as unavailable when the stream is not accessible
- Stream URLs are provided to Home Assistant's camera platform for viewing

Troubleshooting:

- If login fails, double‑check id_site and your PIN. The integration derives cryptographic hashes based on the server-provided salt.
- The integration talks to the official Nexecur endpoints used by the mobile app. If Nexecur changes those endpoints, the integration may need an update.
- If cameras are not discovered, ensure your Nexecur system has streaming enabled and that cameras are properly configured.
- Camera streams may take up to 30 seconds to appear after being added to the system due to the polling interval.

## License

MIT License

Copyright (c) 2025 Loule95450.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

### Legal

This code is in no way affiliated with, authorized, maintained, sponsored or endorsed by Nexecur or any of its affiliates or subsidiaries. This is an independent and unofficial API. Use at your own risk.
