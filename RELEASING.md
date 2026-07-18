# Releasing

## Versioning convention

- Use semantic versioning for `power_watchdog_wifi/manifest.json`.
- Keep changes grouped in `CHANGELOG.md` under `Unreleased` until cut.

## Release checklist

1. Run local checks (`python -m compileall power_watchdog_wifi`, `pytest`, `ruff check .`).
2. Update `CHANGELOG.md` and move release notes from `Unreleased` to a version header.
3. Bump `power_watchdog_wifi/manifest.json` version.
4. Tag the release (`vX.Y.Z`) and publish release notes from changelog content.
