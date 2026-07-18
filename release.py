#!/usr/bin/env python3
"""
Automated release script for Power Watchdog WiFi Home Assistant integration.

This script automates the release process by:
1. Running local checks (compilation, tests, linting)
2. Updating CHANGELOG.md with the new version
3. Bumping the version in manifest.json
4. Committing changes
5. Creating and pushing a git tag
"""

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


class ReleaseManager:
    """Manages the release process."""

    def __init__(self, version: str):
        self.version = version
        self.repo_root = Path(__file__).parent
        self.manifest_path = self.repo_root / "custom_components" / "power_watchdog_wifi" / "manifest.json"
        self.changelog_path = self.repo_root / "CHANGELOG.md"
        self.component_dir = self.repo_root / "custom_components" / "power_watchdog_wifi"

    def run_command(self, cmd: list, description: str) -> bool:
        """Run a command and return success status."""
        print(f"\n📋 {description}...")
        try:
            result = subprocess.run(cmd, cwd=self.repo_root, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ {description} failed:")
                print(result.stdout)
                print(result.stderr)
                return False
            print(f"✅ {description} passed")
            return True
        except Exception as e:
            print(f"❌ Error running {description}: {e}")
            return False

    def run_local_checks(self) -> bool:
        """Run all local checks."""
        print("\n🔍 Running local checks...")

        checks = [
            (
                ["python", "-m", "compileall", str(self.component_dir)],
                "Compilation check"
            ),
            (
                ["python", "-m", "pytest"],
                "pytest"
            ),
            (
                ["python", "-m", "ruff", "check", str(self.component_dir), "tests"],
                "Ruff linting"
            ),
        ]

        for cmd, desc in checks:
            if not self.run_command(cmd, desc):
                return False

        return True

    def validate_version(self) -> bool:
        """Validate version format (semantic versioning)."""
        pattern = r"^\d+\.\d+\.\d+$"
        if not re.match(pattern, self.version):
            print(f"❌ Invalid version format: {self.version}. Use semantic versioning (X.Y.Z)")
            return False
        return True

    def update_manifest(self) -> bool:
        """Update manifest.json with new version."""
        print(f"\n📝 Updating manifest.json to version {self.version}...")
        try:
            with open(self.manifest_path, "r") as f:
                manifest = json.load(f)

            manifest["version"] = self.version

            with open(self.manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)
                f.write("\n")

            print(f"✅ Updated manifest.json")
            return True
        except Exception as e:
            print(f"❌ Failed to update manifest.json: {e}")
            return False

    def update_changelog(self) -> bool:
        """Update CHANGELOG.md by moving Unreleased to version header."""
        print(f"\n📝 Updating CHANGELOG.md...")
        try:
            with open(self.changelog_path, "r") as f:
                content = f.read()

            # Check if Unreleased section exists
            if "## Unreleased" not in content:
                print("❌ No 'Unreleased' section found in CHANGELOG.md")
                return False

            # Replace ## Unreleased with ## [X.Y.Z] - YYYY-MM-DD
            date_str = datetime.now().strftime("%Y-%m-%d")
            updated_content = content.replace(
                "## Unreleased",
                f"## [{self.version}] - {date_str}\n\n## Unreleased"
            )

            # Add a blank Unreleased section if it doesn't exist after our replacement
            if "## Unreleased\n" not in updated_content:
                lines = updated_content.split("\n")
                for i, line in enumerate(lines):
                    if line.startswith(f"## [{self.version}]"):
                        # Insert blank Unreleased section after the new version header
                        lines.insert(i + 1, "")
                        lines.insert(i + 2, "No changes yet.")
                        break
                updated_content = "\n".join(lines)

            with open(self.changelog_path, "w") as f:
                f.write(updated_content)

            print(f"✅ Updated CHANGELOG.md with version {self.version}")
            return True
        except Exception as e:
            print(f"❌ Failed to update CHANGELOG.md: {e}")
            return False

    def commit_changes(self) -> bool:
        """Commit version bump changes."""
        print(f"\n📦 Committing changes...")
        try:
            # Stage files
            subprocess.run(
                ["git", "add", str(self.manifest_path), str(self.changelog_path)],
                cwd=self.repo_root,
                check=True,
                capture_output=True
            )

            # Commit
            subprocess.run(
                ["git", "commit", "-m", f"chore: Release version {self.version}\n\nCo-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"],
                cwd=self.repo_root,
                check=True,
                capture_output=True
            )

            print(f"✅ Committed changes for version {self.version}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to commit changes: {e}")
            return False

    def create_and_push_tag(self) -> bool:
        """Create and push git tag."""
        tag = f"v{self.version}"
        print(f"\n🏷️  Creating and pushing tag {tag}...")
        try:
            # Create annotated tag
            subprocess.run(
                ["git", "tag", "-a", tag, "-m", f"Release {tag}"],
                cwd=self.repo_root,
                check=True,
                capture_output=True
            )

            # Push tag
            subprocess.run(
                ["git", "push", "origin", tag],
                cwd=self.repo_root,
                check=True,
                capture_output=True
            )

            print(f"✅ Created and pushed tag {tag}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create/push tag: {e}")
            print("You may need to push manually: git push origin")
            return False

    def run(self) -> bool:
        """Execute the full release process."""
        print(f"\n🚀 Starting release process for version {self.version}...\n")

        steps = [
            (self.validate_version, "Validate version format"),
            (self.run_local_checks, "Run local checks"),
            (self.update_changelog, "Update CHANGELOG.md"),
            (self.update_manifest, "Update manifest.json"),
            (self.commit_changes, "Commit changes"),
            (self.create_and_push_tag, "Create and push tag"),
        ]

        for step_func, step_name in steps:
            if not step_func():
                print(f"\n❌ Release failed at step: {step_name}")
                return False

        print(f"\n✅ Release {self.version} completed successfully!")
        print(f"\n📌 Next steps:")
        print(f"   1. Monitor GitHub Actions 'Release' workflow to validate tag/version")
        print(f"   2. GitHub Release will be published automatically")
        print(f"   3. HACS will discover the new release")
        return True


def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: python release.py <version>")
        print("Example: python release.py 0.2.0")
        sys.exit(1)

    version = sys.argv[1]
    manager = ReleaseManager(version)

    if not manager.run():
        sys.exit(1)


if __name__ == "__main__":
    main()
