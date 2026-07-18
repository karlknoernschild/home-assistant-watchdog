#!/usr/bin/env python3
"""
Automated release script for Power Watchdog WiFi Home Assistant integration.

Usage:
    python scripts/release.py --version X.Y.Z [--skip-tests]

Steps:
    1. Validates semantic version format
    2. Runs local checks (compile, tests, lint)
    3. Updates CHANGELOG.md (moves Unreleased → version)
    4. Bumps manifest.json version
    5. Commits changes to git
    6. Creates and pushes git tag
    7. Outputs next steps for GitHub Actions release workflow
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


class ReleaseError(Exception):
    """Release process error."""
    pass


def run_command(cmd, description=None):
    """Run shell command and return output."""
    if description:
        print(f"📋 {description}...")
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, check=True
        )
        if result.stdout:
            print(result.stdout.strip())
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr or e.stdout or str(e)
        raise ReleaseError(f"Command failed: {description}\n{error_msg}")


def validate_version(version):
    """Validate semantic version format (X.Y.Z)."""
    if not re.match(r'^\d+\.\d+\.\d+$', version):
        raise ReleaseError(
            f"Invalid version format: {version}\n"
            "Use semantic versioning: X.Y.Z (e.g., 0.2.0)"
        )
    return version


def run_local_checks():
    """Run compile, tests, and linting."""
    checks = [
        ("python -m compileall custom_components/power_watchdog_wifi", "Compiling Python files"),
        ("python -m pytest", "Running tests"),
        ("python -m ruff check custom_components/power_watchdog_wifi tests", "Running linter"),
    ]
    
    for cmd, desc in checks:
        run_command(cmd, desc)


def update_changelog(version):
    """Move Unreleased section to version header in CHANGELOG.md."""
    changelog = Path("CHANGELOG.md")
    if not changelog.exists():
        raise ReleaseError("CHANGELOG.md not found")
    
    content = changelog.read_text()
    
    # Check if Unreleased section exists
    if "## Unreleased" not in content:
        print("⚠️  No 'Unreleased' section in CHANGELOG.md (already released?)")
        return
    
    # Replace Unreleased with version header + date
    today = datetime.now().strftime("%Y-%m-%d")
    new_content = content.replace(
        "## Unreleased",
        f"## [v{version}] - {today}\n\n## Unreleased"
    )
    
    changelog.write_text(new_content)
    print(f"✓ Updated CHANGELOG.md with v{version} ({today})")


def bump_manifest_version(version):
    """Update version in manifest.json."""
    manifest_path = Path("custom_components/power_watchdog_wifi/manifest.json")
    if not manifest_path.exists():
        raise ReleaseError("manifest.json not found")
    
    manifest = json.loads(manifest_path.read_text())
    old_version = manifest.get("version", "unknown")
    manifest["version"] = version
    
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"✓ Updated manifest.json: {old_version} → v{version}")


def commit_and_tag(version):
    """Commit changes and create git tag."""
    # Stage files
    files = ["CHANGELOG.md", "custom_components/power_watchdog_wifi/manifest.json"]
    for f in files:
        run_command(f"git add {f}", f"Staging {f}")
    
    # Commit
    commit_msg = f"Release v{version}"
    run_command(f'git commit -m "{commit_msg}"', f"Committing release")
    
    # Tag
    tag_name = f"v{version}"
    run_command(f'git tag -a {tag_name} -m "Release {tag_name}"', f"Creating tag {tag_name}")
    
    # Push
    run_command("git push origin main", "Pushing main branch")
    run_command(f"git push origin {tag_name}", f"Pushing tag {tag_name}")
    
    print(f"✓ Created and pushed tag: {tag_name}")


def main():
    parser = argparse.ArgumentParser(
        description="Automated release script for Power Watchdog WiFi integration"
    )
    parser.add_argument(
        "--version", required=True, help="Version to release (semantic: X.Y.Z)"
    )
    parser.add_argument(
        "--skip-tests", action="store_true", help="Skip local checks (not recommended)"
    )
    parser.add_argument(
        "--skip-push", action="store_true", help="Skip git push (useful for dry-run)"
    )
    
    args = parser.parse_args()
    
    try:
        # Validate
        version = validate_version(args.version)
        print(f"🚀 Releasing Power Watchdog WiFi v{version}\n")
        
        # Local checks
        if not args.skip_tests:
            print("Running local checks...\n")
            run_local_checks()
            print()
        
        # Update files
        print("Updating release files...\n")
        update_changelog(version)
        bump_manifest_version(version)
        print()
        
        # Git operations
        print("Committing and tagging...\n")
        if args.skip_push:
            print("⏭️  Skipping git push (--skip-push)")
        else:
            commit_and_tag(version)
        
        print(f"\n✅ Release v{version} ready!")
        print("\nNext steps:")
        print("1. Monitor GitHub Actions 'Release' workflow at:")
        print(f"   https://github.com/karlknoernschild/home-assistant-watchdog/actions")
        print("2. Workflow will validate and publish GitHub Release automatically")
        print("3. HACS will detect the new release and surface update to users")
        
    except ReleaseError as e:
        print(f"\n❌ Release failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
