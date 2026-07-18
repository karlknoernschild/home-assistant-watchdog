## Plan: Implement Power Watchdog Next Steps End-to-End

Implement all seven Next Steps by first hardening the data model and coordinator lifecycle, then adding new entities and diagnostics, and finally packaging/testing for HACS + Home Assistant quality expectations. The safest approach is to preserve the strict read-only boundary while introducing richer decoded state, runtime health metrics, and release automation.

**Steps**
1. Phase 1: Baseline and scope lock
1.1 Define acceptance criteria per Next Step item, including which values are mandatory vs best-effort if cloud/protocol fields are unavailable.
1.2 Freeze read-only boundary requirements (no write endpoints, no command methods, no mutation WS actions) and add explicit non-goals for control features.
1.3 Capture a protocol field matrix from existing captures (status/error/heartbeat/device-list fields) and map each requested feature to source field(s) or “unknown/unavailable”.

2. Phase 2: Data-model refactor to support richer state (blocks most downstream work)
2.1 Extend telemetry models to include normalized flag/state fields derived from status_raw and error_raw, while retaining raw values for diagnostics.
2.2 Introduce a coordinator snapshot object that carries:
- Latest telemetry
- Availability state and last telemetry timestamp
- Runtime counters (packet count, decode errors, reconnect count)
- Last connection error and last successful connect time
- Last known device metadata (firmware/cloud/status info)
2.3 Keep backward compatibility for existing sensor value accessors where possible to limit regression risk.

3. Phase 3: Binary sensors and availability behavior
3.1 Add binary sensor platform support and register it alongside sensor platform.
3.2 Implement binary sensor descriptions for each requested status condition where mapping is known; expose “error present” from aggregate error flags.
3.3 For ambiguous conditions (example: relay energized vs power available), implement only after confirmed bit mapping; otherwise mark as deferred with explicit placeholders in docs.
3.4 Add telemetry timeout logic in coordinator to mark snapshot/entities unavailable after a configured interval, and auto-restore immediately on next valid packet.
3.5 Add options/constants for timeout and default thresholds to avoid hard-coded magic values.

4. Phase 4: Expanded device information
4.1 Extend API device-list parsing to normalize metadata fields already returned (version, mcu_version, socket_state, connect_type, start_from, device id/name).
4.2 Decide where attributes should surface:
- Device registry software/hardware version fields (stable identifiers)
- Entity extra state attributes for dynamic values (online/offline, last communication)
4.3 Add a lightweight periodic metadata refresh (or refresh-on-reconnect) using existing read-only device list call, with rate limits to avoid unnecessary API load.
4.4 Populate requested fields when available; where unavailable (example: connection quality granularity), provide null/unknown explicitly rather than guessed values.

5. Phase 5: Diagnostics support with strict redaction
5.1 Add Home Assistant diagnostics entrypoints for config entry and device diagnostics.
5.2 Include firmware/protocol/runtime health data:
- Firmware versions
- Protocol version marker / decoder format version
- Packet counters and decode error counters
- Reconnect count
- Last packet age and last packet timestamp
- Optional measured cloud latency (if implemented)
5.3 Implement recursive redaction for credentials/tokens/account identifiers in all diagnostics payload branches.
5.4 Add unit tests specifically for diagnostics redaction to prevent accidental secret leakage.

6. Phase 6: Energy enhancements (capability-gated)
6.1 Verify source availability for today/yesterday energy and peak-demand metrics from protocol or existing read-only API fields.
6.2 If native fields exist, expose as sensors with proper state classes/device classes.
6.3 If native fields do not exist, compute safe derived metrics locally from cumulative energy/time-series:
- Rolling average power over configurable window
- Daily energy buckets from monotonic counter deltas
6.4 Mark derived metrics clearly in names/attributes/docs to distinguish from device-native values.

7. Phase 7: HACS packaging and release readiness
7.1 Replace placeholder repository links and add final codeowners metadata.
7.2 Add HACS metadata file, semantic versioning process, and changelog/release notes conventions.
7.3 Add CI workflow for lint, type checks, tests, and release tagging.
7.4 Validate install path and metadata requirements for HACS discovery.

8. Phase 8: Home Assistant Quality Scale uplift
8.1 Add test suite structure covering protocol decode, coordinator reconnect/timeout behavior, entity state mapping, diagnostics redaction, and config flow edge cases.
8.2 Add stricter typing and runtime validation at API/protocol boundaries (response schema checks, defensive parsing).
8.3 Add repair issue flow(s) for recurring auth/connectivity/unsupported mapping conditions where user action is possible.
8.4 Improve logging strategy:
- Structured debug logs for packet/connect lifecycle
- Warnings for degraded operation
- No secret-bearing logs
8.5 Complete translations for newly added entities/errors/options and keep strings synchronized.

9. Phase 9: Verification and rollout
9.1 Run local static checks and unit tests.
9.2 Run integration in Home Assistant dev instance with live telemetry and forced disconnect scenarios.
9.3 Validate diagnostics export manually to confirm all redactions.
9.4 Validate HACS install/update from tagged release.
9.5 Cut staged release plan:
- v0.2.x: availability + binary sensor baseline + diagnostics
- v0.3.x: energy enhancements + quality-scale improvements

**Parallelism and dependencies**
1. Blocking chain: Phase 2 -> Phase 3/4/5 -> Phase 6 -> Phase 7/8 -> Phase 9.
2. Parallel work after Phase 2:
- Binary sensors (Phase 3) parallel with expanded metadata (Phase 4)
- Diagnostics payload assembly (Phase 5) parallel with metadata work, but redaction tests must complete before merge
3. HACS packaging (Phase 7) can begin in parallel with late test work (Phase 8), but release tagging waits for Phase 9 verification.

**Relevant files**
- c:/Users/karl/Documents/Projects/PowerWatchdogHomeAssistant/summary.md — Source of Next Steps scope and acceptance checklist.
- c:/Users/karl/Documents/Projects/PowerWatchdogHomeAssistant/power_watchdog_wifi_ha_v0.1.0/custom_components/power_watchdog_wifi/models.py — Extend telemetry structures and add normalized status/error fields.
- c:/Users/karl/Documents/Projects/PowerWatchdogHomeAssistant/power_watchdog_wifi_ha_v0.1.0/custom_components/power_watchdog_wifi/protocol.py — Decode additional raw fields, flag mapping, and protocol version constants.
- c:/Users/karl/Documents/Projects/PowerWatchdogHomeAssistant/power_watchdog_wifi_ha_v0.1.0/custom_components/power_watchdog_wifi/coordinator.py — Add timeout-based availability and runtime counters.
- c:/Users/karl/Documents/Projects/PowerWatchdogHomeAssistant/power_watchdog_wifi_ha_v0.1.0/custom_components/power_watchdog_wifi/sensor.py — Add new numeric/derived energy sensors and metadata attributes.
- c:/Users/karl/Documents/Projects/PowerWatchdogHomeAssistant/power_watchdog_wifi_ha_v0.1.0/custom_components/power_watchdog_wifi/entity.py — Device info enrichment and shared availability behavior.
- c:/Users/karl/Documents/Projects/PowerWatchdogHomeAssistant/power_watchdog_wifi_ha_v0.1.0/custom_components/power_watchdog_wifi/api.py — Metadata refresh and defensive response parsing.
- c:/Users/karl/Documents/Projects/PowerWatchdogHomeAssistant/power_watchdog_wifi_ha_v0.1.0/custom_components/power_watchdog_wifi/const.py — New platform/timeout/options constants.
- c:/Users/karl/Documents/Projects/PowerWatchdogHomeAssistant/power_watchdog_wifi_ha_v0.1.0/custom_components/power_watchdog_wifi/__init__.py — Platform registration and diagnostics wiring.
- c:/Users/karl/Documents/Projects/PowerWatchdogHomeAssistant/power_watchdog_wifi_ha_v0.1.0/custom_components/power_watchdog_wifi/config_flow.py — Optional options flow and validation updates.
- c:/Users/karl/Documents/Projects/PowerWatchdogHomeAssistant/power_watchdog_wifi_ha_v0.1.0/custom_components/power_watchdog_wifi/strings.json — New config/options/errors labels.
- c:/Users/karl/Documents/Projects/PowerWatchdogHomeAssistant/power_watchdog_wifi_ha_v0.1.0/custom_components/power_watchdog_wifi/translations/en.json — Translation entries for new entities/diagnostics/options.
- c:/Users/karl/Documents/Projects/PowerWatchdogHomeAssistant/power_watchdog_wifi_ha_v0.1.0/custom_components/power_watchdog_wifi/manifest.json — Production metadata and repository URLs.
- c:/Users/karl/Documents/Projects/PowerWatchdogHomeAssistant/watchdog_decoded_capture.jsonl — Empirical status/error and packet timing samples for mapping + timeout validation.
- c:/Users/karl/Documents/Projects/PowerWatchdogHomeAssistant/watchdog_websocket_capture.jsonl — WS action flow and heartbeat packet behavior reference.
- c:/Users/karl/Documents/Projects/PowerWatchdogHomeAssistant/watchdog_device_list.json — Available cloud metadata fields for expanded device info.

**Verification**
1. Add and run unit tests for:
- Packet decode and status/error flag mapping
- Coordinator reconnect backoff and timeout availability transitions
- Diagnostics redaction of secrets/tokens
- Config flow and multi-device selection
- Derived energy calculations across day boundaries
2. Run static quality checks (ruff/flake8, mypy/pyright, Home Assistant integration quality checks) in CI.
3. Manual validation in Home Assistant:
- Verify binary sensors toggle correctly under known device states
- Verify entities become unavailable after timeout and recover on telemetry resume
- Verify diagnostics output includes required counters and no secrets
4. HACS validation:
- Fresh install from repo metadata
- Update from one tagged release to next
- Confirm manifest/version/changelog consistency

**Decisions**
- Include: strict read-only telemetry and metadata enrichment, diagnostics, packaging, tests, quality-scale improvements.
- Exclude: any endpoint/action capable of changing relay, settings, ownership, or energy counters.
- Assumption: some requested binary flags and energy fields may require additional reverse-engineering before reliable exposure.

**Further considerations**
1. Binary mapping confidence policy:
- Option A: expose only fully verified flags now (recommended)
- Option B: expose provisional flags marked experimental
2. Energy metrics strategy:
- Option A: native-only metrics (highest accuracy, potentially fewer sensors)
- Option B: allow derived metrics with clear labeling (recommended)
3. Metadata refresh cadence:
- Option A: refresh on reconnect only (lower cloud load)
- Option B: periodic refresh + reconnect refresh (recommended)