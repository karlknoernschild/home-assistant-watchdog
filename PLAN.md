## Plan: Power Watchdog Next Steps Implementation

This plan converts the existing next-steps roadmap into an execution-ready sequence for this repository, with blockers resolved up front: stale paths are replaced with workspace-relative references, availability behavior is moved into the early coordinator baseline, binary sensor scope is limited to verified mappings, and missing project scaffolding (tests/CI/HACS/release files) is explicitly created before validation. The exploratory test-scripts folder is out of implementation scope and excluded from this plan.

**Steps**
1. Phase 0: Readiness gate (must complete before feature coding)
1.1 Replace stale path assumptions from the prior draft with files that exist in this workspace only.
1.2 Define and document verified-only mapping policy for status/error flags:
Only expose binary sensor flags with data-backed confidence from protocol understanding and confirmed runtime behavior.
Keep unknown/unverified bits internal and diagnostic-only.
1.3 Define diagnostics metric policy:
Ship only metrics with a defined producer in current architecture.
Treat cloud latency as deferred unless an unambiguous measurement path is added.
1.4 Add explicit non-goals to preserve read-only safety boundary:
No command methods, no relay control, no write endpoints.
1.5 Scope guard:
Exclude all artifacts under test-scripts from implementation planning and acceptance criteria.

2. Phase 1: Core coordinator/data baseline (blocking)
2.1 Extend telemetry model handling to support coordinator snapshot fields while preserving current sensor compatibility.
2.2 Implement coordinator runtime snapshot with:
Latest telemetry, last telemetry timestamp, reconnect count, decode error count, packet count, last connection error, last successful connect timestamp.
2.3 Implement availability timeout in coordinator as an early baseline behavior:
Entities become unavailable after timeout.
Availability restores on next valid packet.
2.4 Add timeout constants and defaults in constants/config layer first; consider options-flow configurability later.

3. Phase 2: Parallel feature tracks after baseline
3.1 Track A: Binary sensor platform.
Add binary sensor platform registration.
Implement only verified flags first release, including aggregate error-present if confidently derivable.
3.2 Track B: Expanded device info.
Parse and normalize stable fields from device list response (version, mcu_version, connect_type, socket_state, start_from, identifiers).
Refresh metadata on reconnect and/or bounded periodic interval.
3.3 Track C: Diagnostics with redaction.
Add config-entry and device diagnostics payloads.
Include runtime counters and protocol/firmware markers with recursive redaction for account/password/token/device identifiers as appropriate.

4. Phase 3: Energy enhancement gate
4.1 Evaluate source availability for today/yesterday/peak-demand from existing protocol/API evidence in production integration paths.
4.2 If native fields are absent, add only clearly labeled derived metrics (for example rolling-average power and daily delta energy buckets).
4.3 Define derived-metric lifecycle rules:
Rollover behavior at day boundary.
Restart behavior and restoration strategy.

5. Phase 4: Packaging and quality-scale uplift
5.1 Create missing scaffolding before quality checks:
Tests structure, test runner config, lint/type config, CI workflow, HACS metadata, changelog/release convention.
5.2 Replace manifest placeholders with real repository metadata and code owners.
5.3 Add repair-flow handling only where user action can resolve failures (auth/connectivity/mapping unsupported).
5.4 Update strings/translations for all new entities, options, and error text.

6. Phase 5: Verification and staged release
6.1 Automated verification:
Protocol decode coverage, coordinator reconnect/timeout transitions, entity mapping, diagnostics redaction, config-flow selection behavior.
6.2 Manual verification in Home Assistant:
Forced disconnect recovery, timeout availability transitions, metadata refresh behavior, diagnostics export sanity.
6.3 Distribution verification:
HACS fresh install and update path across tagged versions.
6.4 Staged release recommendation:
First release: availability baseline + verified binary sensors + diagnostics.
Second release: energy enhancements + broader quality-scale items.

**Relevant files**
- c:/Users/karl/Documents/GitHub/home-assistant-watchdog/plan.prompt.md - source draft to supersede with this execution-ready plan.
- c:/Users/karl/Documents/GitHub/home-assistant-watchdog/summary.md - authoritative product intent and next-step scope.
- c:/Users/karl/Documents/GitHub/home-assistant-watchdog/power_watchdog_wifi/coordinator.py - availability timeout, reconnect lifecycle, runtime counters.
- c:/Users/karl/Documents/GitHub/home-assistant-watchdog/power_watchdog_wifi/models.py - telemetry/snapshot data structures.
- c:/Users/karl/Documents/GitHub/home-assistant-watchdog/power_watchdog_wifi/protocol.py - decode fields and mapping confidence boundaries.
- c:/Users/karl/Documents/GitHub/home-assistant-watchdog/power_watchdog_wifi/api.py - read-only telemetry stream and metadata refresh hooks.
- c:/Users/karl/Documents/GitHub/home-assistant-watchdog/power_watchdog_wifi/const.py - platform and timeout constants.
- c:/Users/karl/Documents/GitHub/home-assistant-watchdog/power_watchdog_wifi/__init__.py - platform registration and lifecycle wiring.
- c:/Users/karl/Documents/GitHub/home-assistant-watchdog/power_watchdog_wifi/entity.py - shared entity availability/device-info behavior.
- c:/Users/karl/Documents/GitHub/home-assistant-watchdog/power_watchdog_wifi/sensor.py - compatibility baseline for existing sensors and derived additions.
- c:/Users/karl/Documents/GitHub/home-assistant-watchdog/power_watchdog_wifi/config_flow.py - optional timeout/options evolution and validation.
- c:/Users/karl/Documents/GitHub/home-assistant-watchdog/power_watchdog_wifi/manifest.json - placeholder metadata replacement.
- c:/Users/karl/Documents/GitHub/home-assistant-watchdog/power_watchdog_wifi/strings.json - new option/error/entity labels.
- c:/Users/karl/Documents/GitHub/home-assistant-watchdog/power_watchdog_wifi/translations/en.json - synchronized translation coverage.

**Verification**
1. Confirm every referenced file exists in this workspace.
2. Confirm each planned binary sensor has explicit mapping confidence status (verified/deferred).
3. Confirm diagnostics fields each have a defined producer in the current design.
4. Confirm scaffolding creation is scheduled before CI/test execution.
5. Confirm read-only non-goals are retained in docs and architecture notes.
6. Confirm no implementation task depends on files under test-scripts.

**Decisions**
- Included: verified-only binary mappings, early availability baseline, diagnostics with strict redaction, packaging/quality scaffolding creation.
- Deferred: speculative status flags and unsupported native energy metrics without evidence.
- Deferred unless designed: cloud latency metric.
- Safety boundary: strict read-only behavior remains unchanged.
- Scope boundary: test-scripts remains exploratory-only and excluded.

**Further Considerations**
1. Timeout configurability path:
Option A: fixed default first release.
Option B: bounded options-flow setting in same release if UI effort is acceptable.
Recommended: Option A first, Option B next.
2. Derived energy persistence strategy:
Option A: in-memory only.
Option B: recorder-backed restore for daily continuity.
Recommended: Option B if implementation complexity stays low.
3. Binary sensor release strictness:
Option A: only high-confidence flags initially.
Option B: include provisional flags with diagnostic labeling.
Recommended: Option A.