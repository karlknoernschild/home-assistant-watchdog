# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-07-18

## Unreleased

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
