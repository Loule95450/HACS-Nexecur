# Home Assistant (HACS) custom integration

![GitHub release](https://img.shields.io/github/release/Loule95450/HACS-Nexecur.svg)
![GitHub repo size in bytes](https://img.shields.io/github/repo-size/Loule95450/HACS-Nexecur.svg)
![GitHub](https://img.shields.io/github/license/Loule95450/HACS-Nexecur.svg)

This is an unofficial API for the Nexecur system, forked from a deleted repository originally created by Baudev. This fork for HomeAssistant is maintained by Loule95450.

You can now install and use this API as a Home Assistant integration via HACS.

What you get:

- An Alarm control panel entity that shows the current state (armed/disarmed)
- Actions to arm and disarm the alarm from Home Assistant
- Camera stream switch entities to control when camera streams are activated ("Allumer [Camera Name]")
- Camera entities for viewing RTSP streams from Nexecur cameras (when switches are active)
- Automatic polling of the panel status (every 30 seconds by default)
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
- Switch entities like `switch.allumer_{camera_name}` to control camera stream activation
- Camera entities like `camera.nexecur_camera_{site_id}_{serial}` for each camera (when streams are active)

Camera Features:
- Camera streams are controlled by switch entities named "Allumer [Camera Name]"
- Activating a switch requests an RTSP stream from the Nexecur API for that camera
- Switches automatically turn off after 30 seconds (matching API limitations)
- Camera entities only appear and show streams when their corresponding switches are active
- This prevents automatic stream requests that could trigger camera lights unnecessarily
- New cameras are automatically discovered when added to your Nexecur system

Troubleshooting:

- If login fails, double‑check id_site and your PIN. The integration derives cryptographic hashes based on the server-provided salt.
- The integration talks to the official Nexecur endpoints used by the mobile app. If Nexecur changes those endpoints, the integration may need an update.
- If camera switches are not discovered, ensure your Nexecur system has cameras configured and accessible.
- Camera streams only appear when you manually activate the corresponding switch.
- If a camera switch doesn't work, the camera may not support streaming or may be offline.
- Remember that camera switches automatically turn off after 30 seconds to comply with API limitations.

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
