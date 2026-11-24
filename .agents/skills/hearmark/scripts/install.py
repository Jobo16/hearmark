#!/usr/bin/env python3
"""Install Hearmark's local Skill and runtime for Codex and Claude Code."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

VERSION = "0.1.0"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-url", default="https://hearmark.jobo.ink/manifest.json")
    parser.add_argument("--skip-deps", action="store_true", help="Validate Skill placement without installing Python packages")
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1]
    if not (source / "SKILL.md").is_file() or not (source / "scripts/hearmark.py").is_file():
        parser.error("Package is incomplete: skill files are missing")
    if sys.platform != "darwin" or platform.machine() != "arm64":
        parser.error("This beta installer currently supports Apple Silicon Macs only")

    target = Path.home() / ".agents/skills/hearmark"
    if target.exists() or target.is_symlink():
        marker = target / ".hearmark-installed"
        if target.is_symlink() or not marker.is_file():
            parser.error(f"Refusing to replace an unrecognized Skill at {target}")

    claude = Path.home() / ".claude/skills/hearmark"
    if (claude.exists() or claude.is_symlink()) and not (claude.is_symlink() and claude.resolve() == target.resolve()):
        parser.error(f"Refusing to replace an existing Claude Skill at {claude}")

    venv = Path.home() / ".local/share/hearmark/venv"
    if not args.skip_deps:
        venv.parent.mkdir(parents=True, exist_ok=True)
        uv = shutil.which("uv")
        if uv:
            subprocess.run([uv, "venv", "--python", "3.12", str(venv)], check=True)
            subprocess.run([uv, "pip", "install", "--python", str(venv / "bin/python"), "-r", str(source / "requirements.txt")], check=True)
        else:
            subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
            subprocess.run([str(venv / "bin/python"), "-m", "pip", "install", "-r", str(source / "requirements.txt")], check=True)

    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".hearmark-install-", dir=target.parent) as temporary:
        staging = Path(temporary) / "hearmark"
        shutil.copytree(source, staging, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".hearmark-installed"))
        (staging / ".hearmark-installed").write_text(VERSION + "\n", encoding="utf-8")
        backup = Path(temporary) / "previous"
        if target.exists():
            target.rename(backup)
        try:
            staging.rename(target)
        except OSError:
            if backup.exists():
                backup.rename(target)
            raise

    claude.parent.mkdir(parents=True, exist_ok=True)
    if not claude.is_symlink():
        claude.symlink_to(target, target_is_directory=True)

    config = Path.home() / ".config/hearmark/config.json"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(json.dumps({"manifest_url": args.manifest_url, "installed_version": VERSION}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "ok", "version": VERSION, "codex_skill": str(target),
        "claude_skill": str(claude), "runtime": str(venv / "bin/python"),
        "dependencies_installed": not args.skip_deps,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
