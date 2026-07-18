# Releasing

## Versioning convention

- Use semantic versioning for `custom_components/power_watchdog_wifi/manifest.json`.
- Keep changes grouped in `CHANGELOG.md` under `Unreleased` until cut.

## Automated release process

The release process is automated via `release.py`. The script handles:
- Running local checks (compilation, pytest, ruff linting)
- Updating `CHANGELOG.md` with new version and date
- Bumping version in `custom_components/power_watchdog_wifi/manifest.json`
- Committing changes to `main`
- Creating and pushing git tag `vX.Y.Z`

### Running the release script

```bash
python release.py <version>
```

Example:
```bash
python release.py 0.2.0
```

The script will:
1. ✅ Validate version format (semantic versioning X.Y.Z)
2. ✅ Run local checks (compilation, tests, linting)
3. ✅ Update CHANGELOG.md and move notes from `Unreleased` to version header
4. ✅ Bump manifest.json version
5. ✅ Commit changes and push to `main`
6. ✅ Create and push tag `vX.Y.Z`

After the script completes successfully:
- GitHub Actions `Release` workflow validates tag/version and publishes GitHub Release
- HACS update discovery is triggered by the repository release/tag

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
