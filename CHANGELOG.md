# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Changed
- Updated logger information in README.md
- Fixed icon scaling

## [0.5.0] - 2026-07-18

### Added
- Debug log messages now include rich detail: decoded telemetry values (L1/L2 voltage, current, power), WebSocket frame action names, WS close/error message types, and ProtocolError descriptions.
- Logging added to `repairs.py` — issue creation and clearing events are now visible in HA logs.
- Logging added to `sensor.py` and `binary_sensor.py` `async_setup_entry` to confirm platform entity registration at debug level.

### Changed
- Removed the custom log-level integration option. Use HA's built-in **Enable debug logging** button or `logger:` in `configuration.yaml` instead.
- The integration no longer overrides HA's own logger configuration on startup; setting the integration log level option to `inherit` previously cleared any level set via `configuration.yaml`.
- WebSocket JSON parse errors are now logged at debug level instead of being silently swallowed.
- Unexpected errors in the polling loop now include a full traceback in the warning log.

## [0.4.2] - 2026-07-18

- Updated icon

## [0.4.1] - 2026-07-18

### Fixed
- Added local custom-integration brand assets under `custom_components/power_watchdog_wifi/brand/` so Home Assistant can render integration icon/logo from the brand image endpoint.

## [0.4.0] - 2026-07-18

### Added
- Integration options for connection mode: `Polling` (default) or `Always on`.
- Configurable polling interval options: 1, 2, 5, 10, 15, 30, or 60 minutes.
- Focused API test coverage for WebSocket token rejection and one-time re-auth retry.
- Configurable integration log level option (`inherit`, `debug`, `info`, `warning`, `error`).

### Changed
- Updated README with connection-mode behavior, polling defaults/intervals, jitter notes, and dashboard helper requirements.
- Coordinator runtime supports short-lived jittered polling sessions in polling mode.
- Availability timeout is mode-aware to reduce entity flapping between polling cycles.
- Integration now reloads automatically when connection options are changed.
- Added comprehensive structured logging across setup, auth, websocket, polling, availability, and metadata refresh flows.

### Fixed
- WebSocket telemetry now clears stale auth tokens, re-authenticates, and retries once when server-side token login is rejected.

## [0.3.1] - 2026-07-18

- Fixed header ordering issue in release.py 

## [0.3.0] - 2026-07-18

### Added
- Added an example dashboard

## [0.2.0] - 2026-07-18

### Added
- Integration icon (`icon.png`) registered in `manifest.json` for display in the
  Home Assistant UI and HACS.
- Automated release script (`release.py`) covering compilation checks, pytest,
  ruff linting, CHANGELOG and manifest version bumping, commit, and tag push.
- `RELEASING.md` release runbook documenting the automated process and manual
  verification checklist.

### Fixed
- Corrected HACS installation instructions in README to use **Download** instead
  of **Install** to match current HACS UI terminology.

## [0.1.0]

### Added
- Coordinator runtime snapshot, timeout availability baseline, diagnostics, binary
  sensors, expanded metadata refresh, and derived energy metrics.
- CI, lint/type/test scaffolding and HACS metadata.
- Automated verification coverage for protocol decoding, coordinator reconnect and
  timeout transitions, diagnostics redaction, and config-flow device-selection
  behavior.
- Manual/HACS verification checklist and staged release recommendation guidance.
- Repository maturity improvements: MIT license, pre-commit configuration, and
  stricter pytest harness defaults with outbound-network blocking in tests.
- HACS-ready release automation via tag-driven GitHub release workflow and
  improved README installation guidance for one-click HACS install/update flow.
