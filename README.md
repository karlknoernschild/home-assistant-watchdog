# Power Watchdog WiFi for Home Assistant

Experimental, read-only custom integration for Hughes Autoformers Power Watchdog
WiFi models.

## Safety boundary

The client implements only:

- account login
- device listing
- WebSocket login
- WebSocket subscription
- telemetry decoding

It does not implement relay control, energy reset, configuration, rename, add,
delete, share, transfer, or a generic request/command method.

## Installation

1. In Home Assistant, install the **Studio Code Server** app or use the Samba
   share.
2. Copy the folder:
   `custom_components/power_watchdog_wifi`
   into:
   `/config/custom_components/power_watchdog_wifi`
3. Restart Home Assistant.
4. Open **Settings > Devices & services > Add integration**.
5. Search for **Power Watchdog WiFi**.
6. Enter the email address and password used by the official app.

## Entities

- L1/L2 voltage
- L1/L2 current
- Total current (sum of both legs)
- L1/L2 power
- Total power
- L1/L2 accumulated energy
- Total accumulated energy
- Frequency
- L1 error present
- L2 error present
- Error present (aggregate)

## Diagnostics

Diagnostics are available from Home Assistant and include coordinator runtime
counters, protocol markers, and normalized device metadata with recursive
redaction for sensitive account, token, and device identifier fields.

## Data path

This is a cloud-push integration. It authenticates against
`api.watchdogsrv.com` and receives telemetry from
`ws.watchdogsrv.com:5521`.

## Notes

- Credentials are stored in the Home Assistant config entry so the integration
  can reconnect after restarts.
- The WebSocket endpoint currently uses `ws://`, matching the official app.
- This is an independently developed interoperability integration and is not
  affiliated with Hughes Autoformers.
