#!/usr/bin/env python3
"""Install Hearmark's local Skill and link it into an agent's Skill directory."""

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

VERSION = "0.4.0"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-url", default="https://hearmark.jobo.ink/manifest.json")
    parser.add_argument("--agent-skills-dir", type=Path, action="append", default=[], help="Additional user Skill directory for an agent that does not read ~/.agents/skills")
    parser.add_argument("--skip-deps", action="store_true", help="Validate Skill placement without installing Python packages")
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1]
    if not (source / "SKILL.md").is_file() or not (source / "scripts/hearmark.py").is_file():
        parser.error("Package is incomplete: skill files are missing")
    supported = (sys.platform == "darwin" and platform.machine().lower() in ("arm64", "x86_64")) or (sys.platform == "win32" and platform.machine().lower() in ("amd64", "x86_64"))
    if not supported:
        parser.error("Hearmark supports Apple Silicon or Intel Macs and Windows x64")

    target = Path.home() / ".agents/skills/hearmark"
    if target.exists() or target.is_symlink():
        marker = target / ".hearmark-installed"
        if target.is_symlink() or not marker.is_file():
            parser.error(f"Refusing to replace an unrecognized Skill at {target}")

    links = list(dict.fromkeys(root.expanduser().resolve() / "hearmark" for root in args.agent_skills_dir))
    links = [link for link in links if link != target]
    for link in links:
        if (link.exists() or link.is_symlink()) and link.resolve() != target.resolve():
            parser.error(f"Refusing to replace an existing Skill at {link}")

    venv = Path.home() / ".local/share/hearmark/venv"
    runtime = venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if not args.skip_deps:
        venv.parent.mkdir(parents=True, exist_ok=True)
        uv = shutil.which("uv")
        if uv:
            if not runtime.is_file():
                subprocess.run([uv, "venv", "--seed", "--python", "3.12", str(venv)], check=True)
            subprocess.run([uv, "pip", "install", "--python", str(runtime), "-r", str(source / "requirements.txt")], check=True)
        else:
            if sys.version_info < (3, 11):
                parser.error("Python 3.11 or newer is required; install Python 3.12 or uv")
            if not runtime.is_file():
                subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
            subprocess.run([str(runtime), "-m", "pip", "install", "-r", str(source / "requirements.txt")], check=True)

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

    for link in links:
        link.parent.mkdir(parents=True, exist_ok=True)
        if not link.exists():
            if sys.platform == "win32":
                subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], check=True)
            else:
                link.symlink_to(target, target_is_directory=True)

    config = Path.home() / ".config/hearmark/config.json"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(json.dumps({"manifest_url": args.manifest_url, "installed_version": VERSION}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "ok", "version": VERSION, "skill": str(target),
        "linked_skills": [str(link) for link in links], "runtime": str(runtime),
        "dependencies_installed": not args.skip_deps,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
