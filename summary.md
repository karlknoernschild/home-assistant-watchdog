# Power Watchdog WiFi Home Assistant Integration

## Project Summary

This project created a **read-only Home Assistant custom integration**
for the Hughes Autoformers **Power Watchdog WiFi** EMS.

The goal was to expose live electrical telemetry in Home Assistant
**without implementing any functionality capable of controlling the
device**.

The integration now provides live sensors for:

-   L1 Voltage
-   L2 Voltage
-   L1 Current
-   L2 Current
-   Total Current
-   L1 Power
-   L2 Power
-   Total Power
-   L1 Energy
-   L2 Energy
-   Total Energy
-   Frequency

The integration was successfully installed and verified against a live
Power Watchdog. Sensor values matched the official mobile application.

------------------------------------------------------------------------

# Design Principles

The project intentionally follows a strict read-only architecture.

Implemented capabilities:

-   REST login
-   Device discovery
-   WebSocket login
-   WebSocket subscription
-   Telemetry decoding

Not implemented:

-   Relay control
-   Energy reset
-   Configuration changes
-   Device rename
-   Device sharing
-   Device deletion
-   Generic command interface

By omitting write APIs entirely, the integration minimizes the
possibility of accidentally changing the EMS state.

------------------------------------------------------------------------

# Reverse Engineering Process

## 1. APK Analysis

The Android application package (APK) was analyzed to identify:

-   Cloud API endpoints
-   Authentication flow
-   Device discovery
-   WebSocket endpoint
-   Message formats

This eliminated the need to intercept encrypted network traffic.

## 2. REST API Discovery

The following read-only endpoints were identified and validated:

-   `/api/user/login`
-   `/api/device/list`

These are sufficient to authenticate and enumerate devices.

## 3. WebSocket Discovery

Telemetry is delivered through a persistent WebSocket connection.

The integration performs:

1.  WebSocket login
2.  Device subscription
3.  Continuous receipt of report messages

No control messages are transmitted.

## 4. Packet Decoder

The APK contained the packet parsing logic, allowing the telemetry
format to be decoded rather than inferred.

Each telemetry packet contains two 34-byte records representing the two
incoming power legs.

Decoded values include:

-   Voltage
-   Current
-   Power
-   Accumulated energy
-   Frequency
-   Status
-   Error flags

Validation against the official application confirmed the decoded values
matched.

------------------------------------------------------------------------

# Home Assistant Integration

The integration includes:

-   Config Flow
-   Device discovery
-   Device registry support
-   Push coordinator
-   Automatic WebSocket reconnect
-   Sensor entities
-   Packet decoder
-   Read-only cloud client

Communication is entirely cloud-push based.

------------------------------------------------------------------------

# Current Status

## Completed

-   APK reverse engineering
-   Authentication
-   Device discovery
-   WebSocket subscription
-   Packet decoding
-   Live telemetry
-   Home Assistant integration
-   Sensor validation
-   Read-only architecture

The integration is functional and successfully running in Home
Assistant.

------------------------------------------------------------------------

# Next Steps

## 1. Binary Sensors

Decode and expose additional status information such as:

-   Reverse polarity
-   Open neutral
-   Open ground
-   Low voltage
-   High voltage
-   Surge detected
-   Power available
-   Relay energized
-   EMS shutdown
-   Error present

## 2. Expanded Device Information

Populate additional device attributes where available:

-   WiFi firmware
-   Cloud firmware
-   Connection quality
-   Online/offline status
-   Last communication time

## 3. Diagnostics Support

Implement Home Assistant diagnostics including:

-   Firmware versions
-   Protocol version
-   Packet counters
-   Reconnect count
-   Cloud latency
-   Last packet age

All diagnostics should automatically redact credentials and tokens.

## 4. Energy Enhancements

If available from the protocol or cloud:

-   Today's energy
-   Yesterday's energy
-   Peak demand
-   Rolling average power

## 5. Availability Handling

Improve entity availability by:

-   Marking sensors unavailable after telemetry timeout
-   Automatically restoring availability when telemetry resumes

## 6. HACS Packaging

Prepare the integration for public distribution:

-   GitHub repository
-   Releases
-   Versioning
-   HACS metadata
-   Automatic updates

## 7. Home Assistant Quality Scale

Increase compliance with Home Assistant best practices by adding:

-   Unit tests
-   Diagnostics
-   Repair flows
-   Translation completeness
-   Improved logging
-   Strict typing
-   Runtime validation

------------------------------------------------------------------------

# Long-Term Goal

Publish a polished, production-quality, read-only Home Assistant
integration for the Hughes Power Watchdog WiFi that can be installed
through HACS while maintaining a strict safety boundary preventing any
device control operations.
