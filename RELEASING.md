# Releasing

## Versioning convention

- Use semantic versioning for `custom_components/power_watchdog_wifi/manifest.json`.
- Keep changes grouped in `CHANGELOG.md` under `Unreleased` until cut.

## Release checklist

1. Run local checks (`python -m compileall custom_components/power_watchdog_wifi`, `pytest`, `python -m ruff check custom_components/power_watchdog_wifi tests`).
2. Update `CHANGELOG.md` and move release notes from `Unreleased` to a version header.
3. Bump `custom_components/power_watchdog_wifi/manifest.json` version.
4. Commit changes and push to `main`.
5. Create and push tag `vX.Y.Z`.
6. GitHub Actions `Release` workflow validates tag/version and publishes GitHub Release.

## HACS compatibility notes

- Integration code must remain under `custom_components/power_watchdog_wifi`.
- `hacs.json` must remain present and valid at repository root.
- HACS update discovery is driven by repository releases/tags.

## Manual verification in Home Assistant

1. Force a disconnect and verify recovery/reconnect.
2. Verify entities transition unavailable after telemetry timeout and recover on valid packet.
3. Verify refreshed metadata appears after reconnect and periodic refresh.
4. Export diagnostics and confirm payload sanity + expected redaction.

## HACS distribution verification

1. Validate fresh install through HACS from the new tag.
2. Validate update path from prior tag to new tag.
3. Confirm entity registry continuity and expected new entities after update.

## Staged release recommendation

- Release 1: availability baseline + verified binary sensors + diagnostics.
- Release 2: energy enhancements + broader quality-scale items.
