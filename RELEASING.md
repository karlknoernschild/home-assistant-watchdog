# Releasing

## Versioning convention

- Use semantic versioning for `custom_components/power_watchdog_wifi/manifest.json`.
- Keep changes grouped in `CHANGELOG.md` under `Unreleased` until cut.

## Automated release process

Run the release script to automate steps 1–5:

```bash
python scripts/release.py --version X.Y.Z
```

### What the script does:
1. ✓ Validates semantic version format
2. ✓ Runs local checks (compile, tests, lint)
3. ✓ Updates `CHANGELOG.md` (moves `Unreleased` → version header + date)
4. ✓ Bumps `custom_components/power_watchdog_wifi/manifest.json` version
5. ✓ Commits changes to `main`
6. ✓ Creates and pushes git tag `vX.Y.Z`

### Options:
- `--skip-tests`: Skip local checks (not recommended for production releases)
- `--skip-push`: Prepare commit/tag without pushing (dry-run mode)

### Example:
```bash
# Full release
python scripts/release.py --version 0.2.0

# Dry-run (no push)
python scripts/release.py --version 0.2.0 --skip-push
```

### After running the script:
1. Monitor GitHub Actions `Release` workflow at:
   https://github.com/karlknoernschild/home-assistant-watchdog/actions
2. Workflow automatically validates tag/version and publishes GitHub Release
3. HACS detects the release and surfaces update to users

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

